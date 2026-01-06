# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    change_ids = fields.One2many(
        comodel_name='purchase.order.change',
        inverse_name='purchase_id',
        string='Purchase Order Changes'
    )

    def action_open_purchase_order_impact_change(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order Change',
            'res_model': 'purchase.order.change',
            'view_mode': 'form',
            "views": [[self.env.ref('purchase_order_change.view_purchase_order_change_form').id, "form"]],
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_date': fields.Date.today(),
                'default_change_type': 'impact',
            },
        }

    def action_open_purchase_order_change(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order Change',
            'res_model': 'purchase.order.change',
            'view_mode': 'form',
            "views": [[self.env.ref('purchase_order_change.view_purchase_order_change_form').id, "form"]],
            'target': 'new',
            'context': {
                'default_purchase_id': self.id,
                'default_date': fields.Date.today(),
                'default_change_type': 'none',
            },
        }
