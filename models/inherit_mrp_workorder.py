from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime


class MrpWorkOrder(models.Model):
    _inherit='mrp.workorder'
    _description='Mrp Work Order Inherit'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    product_qty = fields.Float(related='production_id.product_qty')
    remaining_qty = fields.Float(string='Quantity After Split')

    def button_finish(self):
        super(MrpWorkOrder, self).button_finish()
        production = self.production_id
        next_work_order = self.find_next_work_order()
        if next_work_order:
            next_work_order.button_start()

    def find_next_work_order(self):
        next_work_order = self.env['mrp.workorder'].search([
            ('production_id', '=', self.production_id.id),
            ('state', '=', 'pending'),
            ('workcenter_id', '>', self.workcenter_id.id),
        ], limit=1, order='workcenter_id')
        return next_work_order