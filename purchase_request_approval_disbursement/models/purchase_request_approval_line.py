from odoo import Command, fields, models


class PurchaseRequestApprovalLine(models.Model):
    _inherit = "purchase.request.approval.line"

    def _prepare_disbursement_request_line_vals(self):
        account = self.product_id._get_disbursement_expense_account()
        return {
            "name": self.name,
            "amount": self.product_qty * self.price_unit,
            "account_id": account.id if account else False,
            "analytic_distribution": self.approval_id.analytic_distribution,
            "tax_ids": [Command.set(self.tax_id.ids)],
        }
