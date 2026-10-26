from odoo import models


class ApprovalRequestAllocation(models.Model):
    _inherit = "approval.request.allocation"

    def _prepare_disbursement_request_line_vals(self):
        return {
            "name": self.description or self.product_id.display_name,
            "amount": self.amount,
            "analytic_distribution": self.request_id.analytic_distribution,
            "partner_id": self.partner_id.id,
            "partner_bank_id": self.partner_bank_id.id or False,
        }
