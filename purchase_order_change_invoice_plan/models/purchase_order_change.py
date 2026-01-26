# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrderChange(models.Model):
    _inherit = 'purchase.order.change'

    @api.model
    def _get_change_type_section_map(self):
        res = super()._get_change_type_section_map()

        res.setdefault("none", []).append(
            "purchase_order_change_committee.purchase_change_section_5"
        )

        return res
