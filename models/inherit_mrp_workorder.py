from odoo import fields, models, api, _
from odoo.exceptions import UserError


class MrpWorkOrderInherit(models.Model):
    _inherit='mrp.workorder'
    _description='Mrp Work Order Inherit'

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    product_qty = fields.Float(related='production_id.product_qty')
    remaining_qty = fields.Float(string='Quantity After Split')


    def record_production(self):
        res = super(MrpWorkorder, self).record_production()
        for move in self.move_raw_ids.filtered(
                lambda mov: mov.state not in ('done', 'cancel')
                and mov.quantity_done > 0):
            context = self._context.copy()
            context['mrp_record_production'] = True
            move.with_context(context)._action_done()
        if not self.next_work_order_id:
            finished_moves = self.production_id.move_finished_ids
            production_moves = finished_moves.filtered(
                lambda x: (x.product_id.id == self.production_id.product_id.id)
                and (x.state not in ('done', 'cancel'))
                and x.quantity_done > 0)
            for production_move in production_moves:
                production_move._action_done()
        return res