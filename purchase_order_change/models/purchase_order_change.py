# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderChange(models.Model):
    _name = 'purchase.order.change'
    _description = 'Purchase Order Change'

    number = fields.Integer(string='Number')
    date = fields.Date(string='Date', default=fields.Date.context_today)
    change_type = fields.Selection(selection=[('none', 'None'), ('impact', 'Impact')])
    section_ids = fields.Many2many(comodel_name="purchase.change.section")
    state = fields.Selection(selection=[("draft", "Draft"), ("done", "Done")] , default="draft")
    purchase_id = fields.Many2one(comodel_name="purchase.order")

    @api.model
    def create(self, vals):
        if vals.get('number', 'New') in (False, 'New'):
            vals['number'] = self.env['ir.sequence'].next_by_code('purchase.order.change') or 'New'
        return super().create(vals)

    def action_done(self):
        for record in self:
            record.state = 'done'

    def action_next(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order (Change)',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'view_id': self.env.ref('purchase_order_change.view_purchase_order_invisible').id,
            'target': 'new',
            'res_id': self.purchase_id.id,
        }
