from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime


class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'
    _description = 'Mrp Work Order Inherit'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    product_qty = fields.Float(related='production_id.product_qty')
    remaining_qty = fields.Float(string='Quantity After Split')


    # Override method button_finish
    def button_finish(self):
        res = super(MrpWorkOrder, self).button_finish()
        production = self.production_id
    
        for record in self:
            # Cek apakah work order saat ini berada di work center Packing dan sudah selesai
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

                production.write({
                    'qty_produced': total_remaining_qty
                })

        # Cari work order berikutnya berdasarkan urutan yang sesuai
        next_work_order = self.find_pending_work_order()
        if next_work_order:
            next_work_order.button_start()
        else:
            next_ready_work_order = self.find_ready_work_order()
            if next_ready_work_order:
                next_ready_work_order

        return res

    def find_pending_work_order(self):
        for record in self:
            return self.env['mrp.workorder'].browse([
                ('production_id', '=', record.production_id.id),
                ('state', '=', 'pending'),
            ])
    
    def find_ready_work_order(self):
        for record in self:
            return self.env['mrp.workorder'].browse([
                ('production_id', '=', record.production_id.id),
                ('state', '=', 'ready'),
            ])

