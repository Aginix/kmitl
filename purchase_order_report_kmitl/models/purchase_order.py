# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'thai.date.mixin']

    def action_open_material_withdrawal_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("พิมพ์ใบเบิกวัสดุ (พ.43)"),
            "res_model": "purchase.order.material.withdrawal.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }
