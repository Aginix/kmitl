from odoo import models


class ApprovalRequestAllocation(models.Model):
    _inherit = "approval.request.allocation"

    def _prepare_disbursement_request_line_vals(self):
        account = (
            self.product_id.property_account_expense_id
            or self.product_id.categ_id.property_account_expense_categ_id
        )
        return {
            "product_id": self.product_id.id,
            "name": self.description or self.product_id.display_name,
            "quantity": 1,
            "price_unit": self.amount,
            "account_id": account.id if account else False,
            "analytic_distribution": self.request_id.analytic_distribution,
            "partner_id": self.partner_id.id,
            "partner_bank_id": self.partner_bank_id.id or False,
        }
