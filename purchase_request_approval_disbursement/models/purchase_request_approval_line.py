from odoo import Command, fields, models


class PurchaseRequestApprovalLine(models.Model):
    _inherit = "purchase.request.approval.line"

    def _prepare_disbursement_request_line_vals(self):
        account = (
            self.product_id.property_account_expense_id
            or self.product_id.categ_id.property_account_expense_categ_id
        )
        return {
            "product_id": self.product_id.id,
            "name": self.name,
            "quantity": self.product_qty,
            "price_unit": self.price_unit,
            "account_id": account.id if account else False,
            "analytic_distribution": self.approval_id.analytic_distribution,
            "tax_ids": [Command.set(self.tax_id.ids)],
        }
