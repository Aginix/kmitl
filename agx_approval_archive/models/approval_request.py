from odoo import _, models

# States in which the reservation is no longer this request's to release: the
# request has reached the disbursement pipeline, where the same commitment is
# carried by the disbursement request (agx_approval_disbursement).
LOCKED_COMMITMENT_STATES = ("to_disburse", "billed")


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def write(self, vals):
        if vals.get("active") is False:
            for record in self.filtered(
                lambda r: r.budget_commitment_id
                and r.state not in LOCKED_COMMITMENT_STATES
            ):
                record._release_budget_commitment(_("archived"))
        return super().write(vals)
