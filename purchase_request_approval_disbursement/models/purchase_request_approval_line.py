from odoo import Command, fields, models


class PurchaseRequestApprovalLine(models.Model):
    _inherit = "purchase.request.approval.line"

    def _prepare_disbursement_request_line_vals(self):
        return {
            "name": self.name,
            "amount": self.product_qty * self.price_unit,
            "analytic_distribution": self.approval_id.analytic_distribution,
            "tax_ids": [Command.set(self.tax_id.ids)],
        }
