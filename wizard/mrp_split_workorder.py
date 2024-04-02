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

    # """Untuk menampilkan workorder_id, workcenter_id, dan workcenter_capacity berdasarkan Manufacturing Order
    # dari field production_id"""
    # @api.onchange('production_id')
    # def _onchange_production_id(self):
    #     if self.production_id:            
    #         workorder = self.production_id.workorder_ids.filtered(lambda w: w.operation_id.workcenter_id)
    #         if workorder:
    #             self.workorder_id = workorder[0]
    #             self.workcenter_id = workorder[0].operation_id.workcenter_id
    #             self.workcenter_capacity = workorder[0].operation_id.workcenter_id.capacity
                    

    """Masih memiliki kekeliruan pada rumus dalam melakukan pembagian / split work order , 
    quantity untuk masing-masing work order hasil split masih menampilkan quantity to produce 
    secara keseluruhan."""
            
    def action_split_workorder(self):
        for record in self:
            if record.qty_to_split <= 0:
                continue
            
            # Ambil Work Order yang akan dibagi
            workorder = record.workorder_id
            production_id = record.production_id

            # Validasi kapasitas Work Center
            if record.workcenter_capacity <= 0:
                raise UserError("Kapasitas Work Center tidak valid atau nol.")

            total_qty_to_produce = production_id.product_qty 
            qty_per_workorder = total_qty_to_produce // record.qty_to_split

            # Hitung jumlah Work Order yang akan dibuat
            num_wo = total_qty_to_produce // qty_per_workorder
            remainder = total_qty_to_produce % qty_per_workorder

            # Konversi nilai float menjadi integer
            num_wo = int(num_wo)

            # Daftar Work Order baru yang akan dibuat
            new_workorders = []

            # Split Work Order berdasarkan kapasitas Work Center
            for i in range(num_wo):
                quantity_to_produce = qty_per_workorder
                if i < remainder:
                    quantity_to_produce += 1

                # Buat Work Order baru berdasarkan data dari Work Order yang sudah ada
                new_workorder = workorder.copy(default={
                    'name': '%s (Split %s)' % (workorder.name, i + 1),
                    'product_qty': quantity_to_produce,
                })
                new_workorders.append(new_workorder.id)

            # Kembalikan aksi untuk menampilkan hasil split work order
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








