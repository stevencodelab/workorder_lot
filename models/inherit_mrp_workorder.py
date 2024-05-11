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
        else:
            if not self.find_pending_work_order() and not self.find_ready_work_order():
                first_work_order = self.find_first_work_order()
                if first_work_order:
                    first_work_order.button_start()
    
    def find_first_work_order(self):
        first_work_order = self.env['mrp.workorder'].search([
            ('production_id', '=', production_id.id),
            ('state', '=', 'ready'),
            ('workcenter_id', '>', self.workcenter_id.id),
        ], limit=1, order='workcenter_id')
        return first_work_order

    def find_next_work_order(self):
        next_work_order = self.env['mrp.workorder'].search([
            ('production_id', '=', production_id.id),
            ('state', '=', 'ready'),
            ('workcenter_id', '>', self.workcenter_id.id),
        ], limit=1, order='workcenter_id')

        if next_work_order:
            return next_work_order
        else:
            pending_work_order = self.env['mrp.workorder'].search([
                ('production_id', '=', production_id.id),
                ('state', '=', 'pending'),
                ('workcenter_id', '>', self.workcenter_id.id),
            ], limit=1, order='workcenter_id')
            return pending_work_order


    def find_pending_work_order(self):
        pending_work_order = self.env['mrp.workorder'].search([
            ('production_id', '=', self.production_id.id),
            ('state', '=', 'pending'),
        ])
        return pending_work_order

    def find_ready_work_order(self):
        ready_work_order = self.env['mrp.workorder'].search([
            ('production_id', '=', self.production_id.id),
            ('state', '=', 'ready'),
        ])
        return ready_work_order