from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime

class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'
    _description = 'Mrp Work Order Inherit'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    product_qty = fields.Float(related='production_id.product_qty')
    remaining_qty = fields.Float(string='Quantity After Split')

    def button_finish(self):
        res = super(MrpWorkOrder, self).button_finish()
        production = self.production_id

        # Cari work order berikutnya dan mulai jika ada
        next_work_order = self.find_next_work_order()
        if next_work_order:
            next_work_order.button_start()
    
        # Cari work order yang ready dan mulai jika ada
        ready_work_order = self.find_ready_work_order()
        if ready_work_order:
            ready_work_order

        for record in self:
            # Jika work order saat ini di Packing dan selesai, tambahkan ke qty_produced
            if record.workcenter_id.name == 'PACKING' and record.state == 'done':
                # Ambil nilai remaining_qty dari work order saat ini
                remaining_qty = record.remaining_qty

                # Update nilai qty_producing dengan remaining_qty
                record.qty_producing = remaining_qty

                # Perbarui nilai qty_produced pada MO dengan total remaining_qty dari semua work order di Packing yang sudah selesai
                total_remaining_qty = sum(self.env['mrp.workorder'].search([
                    ('production_id', '=', production.id),
                    ('workcenter_id.name', '=', 'PACKING'),
                    ('state', '=', 'done')
                ]).mapped('remaining_qty'))

                # Ambil nilai product_qty dari MO
                product_qty = production.product_qty

                # Pastikan total_remaining_qty tidak melebihi product_qty pada MO

                production.write({
                    'qty_producing': remaining_qty
                })
    
        return res
    
    def find_first_work_order(self):
        for record in self:
            first_work_order = self.env['mrp.workorder'].search([
                ('production_id', '=', record.production_id.id),
                ('state', '=', 'ready'),
                ('workcenter_id', '>', record.workcenter_id.id),
            ], limit=1, order='workcenter_id')
            if first_work_order:
                return first_work_order
        return False
    
    def find_next_work_order(self):
        for record in self:
            next_work_order = self.env['mrp.workorder'].search([
                ('production_id', '=', record.production_id.id),
                ('state', '=', 'pending'),
                ('workcenter_id', '>', record.workcenter_id.id),
            ], limit=1, order='workcenter_id')
            if next_work_order:
                return next_work_order
        return False

    def find_pending_work_order(self):
        for record in self:
            pending_work_order = self.env['mrp.workorder'].search([
                ('production_id', '=', record.production_id.id),
                ('state', '=', 'pending'),
            ], limit=1)
            if pending_work_order:
                return pending_work_order
        return False
    
    def find_ready_work_order(self):
        for record in self:
            ready_work_order = self.env['mrp.workorder'].search([
                ('production_id', '=', record.production_id.id),
                ('state', '=', 'ready'),
            ], limit=1)
            if ready_work_order:
                return ready_work_order
        return False

