# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _lt, api, fields, models

RECTOR_DELEGATE_GROUP = "disbursement.group_disbursement_rector_delegate"


class DisbursementRequest(models.Model):
    """The ผู้รับมอบอำนาจอธิการบดี act: the Rector-delegated approver approves.
    Independent of the other acts and of the budget: consuming the budget is
    disbursement_budget's own act."""

    _inherit = "disbursement.request"

    rector_approver_id = fields.Many2one(
        "res.users", string="Rector-delegated Approver", copy=False, readonly=True
    )
    rector_approve_date = fields.Datetime(
        string="Rector Approved On", copy=False, readonly=True
    )

    can_approve_rector = fields.Boolean(compute="_compute_can_approve_rector")

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.approve_rector",
                "name": _lt("Approve (Rector Delegate)"),
                "kind": "act",
                "group": RECTOR_DELEGATE_GROUP,
                "sequence": 30,
                "module": "disbursement_approver_rector",
            }
        ]

    @api.depends("state")
    @api.depends_context("uid")
    def _compute_can_approve_rector(self):
        for rec in self:
            rec.can_approve_rector = rec._disbursement_act_offered(
                "disbursement.approve_rector"
            )

    def action_approve(self):
        """The act: record the Rector-delegated approver's sign-off."""
        for rec in self:
            rec._disbursement_check_act("disbursement.approve_rector")
            rec.rector_approver_id = self.env.user
            rec.rector_approve_date = fields.Datetime.now()
            rec._stamp_signature("rector_approve")
            rec._disbursement_act_done("disbursement.approve_rector")
        return True

    def action_draft(self):
        res = super().action_draft()
        self.filtered("rector_approver_id").write(
            {"rector_approver_id": False, "rector_approve_date": False}
        )
        return res
