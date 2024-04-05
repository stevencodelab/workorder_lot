from odoo import _, models, fields, api
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    production_capacity = fields.Float(compute='_compute_production_capacity', help="Quantity that can be produced with the current stock of components")
    document_id = fields.Many2one('msp.documents.id', string="Documents ID", copy=False, readonly=False)
    doc_ids = fields.Char(related='document_id.doc_name', string="Document ID")
    partner_id = fields.Many2one('res.partner', 'Customer')

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