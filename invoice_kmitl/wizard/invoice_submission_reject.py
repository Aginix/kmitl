# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class InvoiceSubmissionReject(models.TransientModel):
    _name = "kmitl.invoice.submission.reject"
    _description = "Reject Invoice Submission"

    submission_id = fields.Many2one(
        "kmitl.invoice.submission",
        string="Submission",
        required=True,
        readonly=True,
    )
    reason = fields.Text(string="Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        submission = self.submission_id
        if submission.state != "submitted":
            raise UserError(_("Only submitted submissions can be rejected."))
        submission._check_approver()
        submission.message_post(
            body=_("Submission rejected by %(user)s.<br/>Reason: %(reason)s")
            % {"user": self.env.user.name, "reason": self.reason},
        )
        submission._reset()
        return True
