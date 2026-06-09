# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseCreateInvoicePlan(models.TransientModel):
    _inherit = "purchase.create.invoice.plan"

    interval = fields.Integer(default=0)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self._context.get("active_id")
        if active_id and "installment_date" in fields_list:
            purchase = self.env["purchase.order"].browse(active_id)
            if purchase.work_start:
                res["installment_date"] = purchase.work_start
        return res
