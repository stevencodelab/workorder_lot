from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, format_datetime

class MrpSplitWorkOrder(models.TransientModel):
    _name ='mrp.split.work.order'
    _description = 'Split Work Order'

    
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', store=True, copy=False)
    product_qty = fields.Float(related='production_id.product_qty')
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

    def action_split(self):
        workorders = []
        for record in self:
            total_qty = record.product_qty
            capacity = record.workcenter_capacity
            qty_to_produce = record.quantity_to_produce
            qty_per_wo = int(total_qty / capacity)
            remaining_qty = total_qty % capacity

            for i in range(qty_per_wo):
                name = '%s (Splited %s)' % (record.production_id.name, i + 1)
                product_qty = capacity
                workorder = record.production_id.workorder_ids.create({
                    'name': name,
                    'product_id': record.product_id.id,
                    'product_qty': product_qty,
                    'workcenter_id': record.workcenter_id.id,
                    'state': 'ready',
                })
                workorders.append(workorder.id)

            if remaining_qty > 0:
                name = '%s (Splited %s)' % (record.production_id.name, qty_per_wo + 1)
                product_qty = remaining_qty
                workorder = record.production_id.workorder_ids.create({
                    'name': name,
                    'product_id': record.product_id.id,
                    'product_qty': product_qty,
                    'workcenter_id': record.workcenter_id.id,
                    'state': 'ready',  
                })
                workorders.append(workorder.id)

            record.production_id.qty_producing -= qty_to_produce

        # Return action to open created Work Orders
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