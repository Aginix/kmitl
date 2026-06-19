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

    def action_open_purchase_order_change(self):
        change_type = self.env.context.get("change_type", "none")
        return self._action_open_purchase_order_change(change_type)

    def _action_open_purchase_order_change(self, change_type):
        self.ensure_one()

        name = (
            _("Structural Contract Change")
            if change_type == "impact"
            else _("Non-Structural Contract Change")
        )

        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "purchase.order.change",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref(
                        "purchase_order_change.view_purchase_order_change_form"
                    ).id,
                    "form",
                )
            ],
            "target": "new",
            "context": self._get_purchase_order_change_context(change_type),
        }

    def _get_purchase_order_change_context(self, change_type):
        self.ensure_one()

        return {
            "default_purchase_id": self.id,
            "default_date": fields.Date.today(),
            "default_change_type": change_type,
        }
