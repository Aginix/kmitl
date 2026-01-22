# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderChange(models.Model):
    _inherit = 'purchase.order.change'

    @api.model
    def _get_change_type_section_map(self):
        res = super()._get_change_type_section_map()

        res.setdefault("none", []).append(
            "purchase_order_change_committee.purchase_change_section_4"
        )

        return res

    def _prepare_wizard_context(self, extra_context=None):
        context = super()._prepare_wizard_context(extra_context=extra_context)

        purchase = self.purchase_id
        if purchase and purchase.work_acceptance_committee_ids:
            context.update({
                "default_work_acceptance_committee_ids": [
                    (6, 0, purchase.work_acceptance_committee_ids.ids)
                ]
            })

        return context
