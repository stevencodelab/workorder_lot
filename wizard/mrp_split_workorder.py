from odoo import _, models, fields, api
from odoo.exceptions import UserError

class MrpSplitWorkOrder(models.TransientModel):
    _name ='mrp.split.work.order'
    _description = 'Split Work Order'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', store=True, copy=False)
    product_qty = fields.Float(related='production_id.product_qty')
    product_id = fields.Many2one(related='production_id.product_id', string='Product')
    quantity_to_produce = fields.Float(related='production_id.product_qty', string='Quantity To Produce')
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order')
    workcenter_id = fields.Many2one('mrp.workcenter', string="Work Center")
    workcenter_capacity = fields.Float(related='workcenter_id.capacity', string="Work Center Capacity")
    qty_to_split = fields.Integer(string="Split Into ?")
    production_detailed_vals_ids = fields.One2many('mrp.production.split.line', 'mrp_production_split_id', 'Split Details', compute="_compute_details", store=True, readonly=False)
    production_split_multi = fields.Many2one('mrp.production.split.multi', 'Split Productions')


    """function for split the work order into smaller based on the quantity_to_split.
    the logic in this function still need to be fix."""

    def action_split_workorder(self):
        new_workorders = []

        for record in self:
            workorder = record.workorder_id
            total_qty_to_produce = record.production_id.product_qty
            qty_to_split = record.qty_to_split

            self.production_id.qty_producing -= self.qty_to_split
            qty_per_work_order = int(total_qty_to_produce // qty_to_split)

            for i in range(int(qty_to_split)):
                new_name = workorder.copy(default={
                    'name': '%s (Split %s)' % (workorder.name, i + 1),
                    'product_qty': qty_per_work_order,
                })
                new_workorders.append(new_name.id) 

            for new_workorder in self.env['mrp.workorder'].browse(new_workorders):
                new_workorder.product_qty = qty_per_work_order

        return {
            'name': 'Work Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', new_workorders)],
        }


    @api.depends('production_detailed_vals_ids')
    def _compute_counter(self):
        for wizard in self:
            wizard.qty_to_split = len(wizard.production_detailed_vals_ids)

    @api.depends('qty_to_split')
    def _compute_details(self):
        for record in self:
            split = []
            if record.qty_to_split < 1 or not record.production_id:
                record.production_detailed_vals_ids = split
                continue
            quantity = record.quantity_to_produce / record.qty_to_split
            remaining_quantity = record.quantity_to_produce
            for _ in range(record.qty_to_split - 1):
                split.append((0, 0, {
                    'quantity': quantity,
                    'user_id': record.production_id.user_id.id,
                    'date': record.production_id.date_start,
                }))
                remaining_quantity -= quantity
            split.append((0, 0, {
                'quantity': remaining_quantity,
                'user_id': record.production_id.user_id.id,
                'date': record.production_id.date_start,
            }))
            record.production_detailed_vals_ids = split

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
    

    mrp_production_split_id = fields.Many2one('mrp.production.split', 'Split Production', required=True, ondelete="cascade")
    quantity = fields.Float('Quantity To Produce', digits='Product Unit of Measure', required=True)
    user_id = fields.Many2one('res.users', 'Responsible', domain=lambda self: [('groups_id', 'in', self.env.ref('mrp.group_mrp_user').id)])
    date = fields.Datetime('Schedule Date')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    product_id = fields.Many2one(related='production_id.product_id')








