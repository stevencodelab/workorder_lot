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
        res = super(MrpWorkOrder, self).button_finish()
        end_date = datetime.now()
        for workorder in self:
            if workorder.state in ('done', 'cancel'):
                continue
            workorder.end_all()
            vals = {
                'qty_produced': workorder.qty_produced or workorder.qty_producing or workorder.qty_production,
                'state': 'done',
                'date_finished': end_date,
                'date_planned_finished': end_date
            }
            if not workorder.date_start:
                vals['date_start'] = end_date
            if not workorder.date_planned_start or end_date < workorder.date_planned_start:
                vals['date_planned_start'] = end_date
            workorder.with_context(bypass_duration_calculation=True).write(vals)

            # Menambahkan logika untuk menentukan Work Order berikutnya yang "Ready"
            next_work_order = workorder._get_next_work_order()
            if next_work_order:
                next_work_order.state = 'ready'

        return True
        return res

    def _get_next_work_order(self):
        # Mengembalikan Work Order berikutnya yang "Ready" untuk dilanjutkan
        next_work_order = self.env['mrp.workorder'].search([
            ('production_id', '=', self.production_id.id),
            ('state', '=', 'pending'),
        ], limit=1, order='sequence')
        return next_work_order