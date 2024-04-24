from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    production_capacity = fields.Float(compute='_compute_production_capacity', help="Quantity that can be produced with the current stock of components")
    document_id = fields.Many2one('msp.documents.id', string="Documents ID", copy=False, readonly=False)
    doc_ids = fields.Char(related='document_id.doc_name', string="Document ID")
    partner_id = fields.Many2one('res.partner', 'Customer')
    # split_workorder = fields.Many2one('mrp.split.work.order', 'Split Wo')
    sample_dev_id = fields.Many2one('msp.sample.dev', 'Sample Development', store=True)
    sample_style = fields.Char(related='sample_dev_id.style', string="Style")
    warna_sample = fields.Char(related='sample_dev_id.warna', string="Warna")
    sample_size = fields.Float(related='sample_dev_id.size', string="Size")

    def _get_sample_dev_id(self):
        for production in self:
            product_id = production.product_id.id
            sample_dev_data = self.env['msp.sample.dev'].search([('product_id', '=', product_id)], limit=1)
            if sample_dev_data:
                production.sample_dev_id = sample_dev_data.id
            else:
                production.sample_dev_id = False

    """action to open to Split Production form"""
    def action_split(self):
        self._pre_action_split_merge_hook(split=True)
        if len(self) > 1:
            productions = [Command.create({'production_id': production.id}) for production in self]
            # Wizard need a real id to have buttons enable in the view
            wizard = self.env['workorder_lot.mrp.production.split.multi'].create({'production_ids': productions})
            action = self.env['ir.actions.actions']._for_xml_id('workorder_lot.action_mrp_production_split_multi')
            action['res_id'] = wizard.id
            return action
        else:
            action = self.env['ir.actions.actions']._for_xml_id('workorder_lot.action_mrp_production_split')
            action['context'] = {
                'default_production_id': self.id,
            }
            return action

    def action_merge(self):
            self._pre_action_split_merge_hook(merge=True)
            products = set([(production.product_id, production.bom_id) for production in self])
            product_id, bom_id = products.pop()
            users = set([production.user_id for production in self])
            if len(users) == 1:
                user_id = users.pop()
            else:
                user_id = self.env.user
    
            origs = self._prepare_merge_orig_links()
            dests = {}
            for move in self.move_finished_ids:
                dests.setdefault(move.byproduct_id.id, []).extend(move.move_dest_ids.ids)
    
            production = self.env['mrp.production'].with_context(default_picking_type_id=self.picking_type_id.id).create({
                'product_id': product_id.id,
                'bom_id': bom_id.id,
                'picking_type_id': self.picking_type_id.id,
                'product_qty': sum(production.product_uom_qty for production in self),
                'product_uom_id': product_id.uom_id.id,
                'user_id': user_id.id,
                'origin': ",".join(sorted([production.name for production in self])),
            })
    
            for move in production.move_raw_ids:
                for field, vals in origs[move.bom_line_id.id].items():
                    move[field] = vals

            for move in production.move_finished_ids:
                move.move_dest_ids = [Command.set(dests[move.byproduct_id.id])]

            self.move_dest_ids.created_production_id = production.id

            self.procurement_group_id.stock_move_ids.group_id = production.procurement_group_id

            if 'confirmed' in self.mapped('state'):
                production.move_raw_ids._adjust_procure_method()
                (production.move_raw_ids | production.move_finished_ids).write({'state': 'confirmed'})
                production.action_confirm()

            self.with_context(skip_activity=True)._action_cancel()
            # set the new deadline of origin moves (stock to pre prod)
            production.move_raw_ids.move_orig_ids.with_context(date_deadline_propagate_ids=set(production.move_raw_ids.ids)).write({'date_deadline': production.date_start})
            for p in self:
                p._message_log(body=_('This production has been merge in %s', production.display_name))

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'view_mode': 'form',
                'res_id': production.id,
            }        

    def _pre_action_split_merge_hook(self, merge=False, split=False):
            if not merge and not split:
                return True
            ope_str = merge and _('merged') or _('split')
            if any(production.state not in ('draft', 'confirmed') for production in self):
                raise UserError(_("Only manufacturing orders in either a draft or confirmed state can be %s.", ope_str))
            if any(not production.bom_id for production in self):
                raise UserError(_("Only manufacturing orders with a Bill of Materials can be %s.", ope_str))
            if split:
                return True

            if len(self) < 2:
                raise UserError(_("You need at least two production orders to merge them."))
            products = set([(production.product_id, production.bom_id) for production in self])
            if len(products) > 1:
                raise UserError(_('You can only merge manufacturing orders of identical products with same BoM.'))
            additional_raw_ids = self.mapped("move_raw_ids").filtered(lambda move: not move.bom_line_id)
            additional_byproduct_ids = self.mapped('move_byproduct_ids').filtered(lambda move: not move.byproduct_id)
            if additional_raw_ids or additional_byproduct_ids:
                raise UserError(_("You can only merge manufacturing orders with no additional components or by-products."))
            if len(set(self.mapped('state'))) > 1:
                raise UserError(_("You can only merge manufacturing with the same state."))
            if len(set(self.mapped('picking_type_id'))) > 1:
                raise UserError(_('You can only merge manufacturing with the same operation type'))
            # TODO explode and check no quantity has been edited
            return True   

    """Override _create_workorder function from model mrp.production to model mrp.split.work.order"""         
    def _create_workorder(self):
        res = super(MrpProduction, self)._create_workorder()
        
        # Panggil metode untuk membagi work order
        for production in self:
            split_workorder = production.split_workorder
            if split_workorder:
                split_workorder.action_split()

        return res

class MrpSplitWorkOrder(models.TransientModel):
    _name ='mrp.split.work.order'
    _description = 'Split Work Order'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', store=True, copy=False)
    product_qty = fields.Float(related='workorder_id.product_qty')
    product_id = fields.Many2one(related='production_id.product_id', string='Product')
    quantity_to_produce = fields.Float(related='production_id.product_qty', string='Quantity To Produce')
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order')
    product_uom_id = fields.Many2one(related='production_id.product_uom_id')
    qty_to_split = fields.Integer(string="Split Into ?",readonly=False,  copy=False, store=True, compute="_compute_counter")
    production_detailed_vals_ids = fields.One2many('mrp.production.split.line', 'mrp_production_split_id', 'Split Details', compute="_compute_details", store=True, readonly=False)
    production_split_multi = fields.Many2one('mrp.production.split.multi', 'Split Productions')
    quantity_to_produce = fields.Float(related='production_id.product_qty', string='Quantity To Produce')
    workcenter_id = fields.Many2one('mrp.workcenter', string="Work Center")
    workcenter_capacity = fields.Float(related='workcenter_id.capacity', string="Work Center Capacity")

    """function for split the work order into smaller based on the qty_to_split.
    the logic in this function still need to be fix."""

    def action_split_workorder(self):
        workorders = []
        for record in self:
            total_qty = record.product_qty
            capacity = record.workcenter_id.capacity
            qty_per_wo = int(total_qty // capacity)
            remaining_qty = total_qty % capacity 

            # Membuat work order utama
            for i in range(qty_per_wo):
                name = '%s (Split %s)' % (record.workorder_id.name, i + 1)
                product_qty = capacity
                workorder = record.production_id.workorder_ids.create({
                    'name': name,
                    'product_id': record.product_id.id,
                    'product_qty': product_qty,
                    'workcenter_id': record.workcenter_id.id,
                    'product_uom_id': record.product_id.uom_id.id,
                    'state': 'ready',
                    'remaining_qty' : capacity,
                })
                workorders.append(workorder.id)

            if remaining_qty > 0:
                name = '%s (Split %s)' % (record.workorder_id.name, qty_per_wo + 1)
                product_qty = remaining_qty
                workorder = record.production_id.workorder_ids.create({
                    'name': name,
                    'product_id': record.product_id.id,
                    'product_qty': product_qty,
                    'workcenter_id': record.workcenter_id.id,
                    'product_uom_id': record.product_id.uom_id.id,
                    'state': 'ready',
                    'remaining_qty' : remaining_qty,
                })
                workorders.append(workorder.id)

                print("Total Quantity:", total_qty)
                print("Work Center Capacity:", capacity)
                print("Quantity per Work Order:", qty_per_wo)
                print("Remaining Quantity:", remaining_qty)

        return {
            'name': 'Work Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', workorders)],
        }


    @api.depends('production_detailed_vals_ids')
    def _compute_counter(self):
        for wizard in self:
            wizard.qty_to_split = len(wizard.production_detailed_vals_ids)

    @api.depends('qty_to_split')
    def _compute_details(self):
        for wizard in self:
            commands = []
            if wizard.qty_to_split < 1 or not wizard.production_id:
                wizard.production_detailed_vals_ids = commands
                continue
            quantity = float_round(wizard.product_qty / wizard.qty_to_split, precision_rounding=wizard.product_uom_id.rounding)
            remaining_quantity = wizard.product_qty
            for _ in range(wizard.qty_to_split - 1):
                commands.append((0, 0, {
                    'quantity': quantity,
                    'user_id': wizard.production_id.user_id.id,
                    'production_id': wizard.production_id.name,
                }))
                remaining_quantity = float_round(remaining_quantity - quantity, precision_rounding=wizard.product_uom_id.rounding)
            commands.append((0, 0, {
                'quantity': remaining_quantity,
                'user_id': wizard.production_id.user_id.id,
                'production_id': wizard.production_id.name,
            }))
            wizard.production_detailed_vals_ids = commands
    
    @api.depends('production_detailed_vals_ids')
    def _compute_valid_details(self):
        for record in self:
            if record.production_detailed_vals_ids:
                record.valid_details = record.quantity_to_produce == sum(record.production_detailed_vals_ids.mapped('quantity'))

class MrpProductionSplitMulti(models.TransientModel):
    _name = 'mrp.production.split.multi'
    _description = "Wizard to Split Multiple Productions"

    production_ids = fields.One2many('mrp.split.work.order', 'production_split_multi', 'Productions To Split')

class MrpProductionSplitLine(models.TransientModel):
    _name='mrp.production.split.line'
    _description='Mrp Production Split Line'    
    
    mrp_production_split_id = fields.Many2one('mrp.split.work.order', 'Split Production', required=True, ondelete="cascade")
    quantity = fields.Float('Quantity Each WO', digits='Product Unit of Measure', required=True)
    user_id = fields.Many2one('res.users', 'Responsible', domain=lambda self: [('groups_id', 'in', self.env.ref('mrp.group_mrp_user').id)])
    date = fields.Datetime('Schedule Date')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    product_id = fields.Many2one(related='production_id.product_id')