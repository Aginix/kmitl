from odoo import _, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def write(self, vals):
        if vals.get("active") is False:
            for record in self.filtered("budget_commitment_id"):
                record._release_budget_commitment(_("archived"))
        return super().write(vals)
