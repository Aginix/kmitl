# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderChange(models.Model):
    _inherit = 'purchase.order.change'

    @api.model
    def _get_change_type_section_map(self):
        res = super()._get_change_type_section_map()

        res.setdefault("none", []).append(
            "purchase_order_change_invoice_plan.purchase_change_section_5"
        )

        return res

    def _prepare_wizard_context(self, extra_context=None):
        self.ensure_one()

        base_context = {
            "default_invoice_plan_ids": [
                (0, 0, {
                    "installment": plan.installment,
                    "plan_date": plan.plan_date,
                    "percent": plan.percent,
                    "invoice_plan_id": plan.id,
                })
                for plan in self.purchase_id.invoice_plan_ids
            ],
        }

        if extra_context:
            base_context.update(extra_context)

        return base_context
