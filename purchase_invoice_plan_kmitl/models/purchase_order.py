from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def create_invoice_plan(
        self, num_installment, installment_date, interval, interval_type
    ):
        res = super().create_invoice_plan(
            num_installment, installment_date, interval, interval_type
        )
        self.invoice_plan_ids.write({"plan_date": False})
        return res
