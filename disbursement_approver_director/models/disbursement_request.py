# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _lt, api, fields, models

FINANCE_DIRECTOR_GROUP = "disbursement.group_disbursement_finance_director"


class DisbursementRequest(models.Model):
    """The ผอ.กองคลัง act: the Finance Division Director approves.

    Independent of the validate act: a request that was never validated can be
    approved here."""

    _inherit = "disbursement.request"

    finance_approver_id = fields.Many2one(
        "res.users", string="Finance Director", copy=False, readonly=True
    )
    finance_approve_date = fields.Datetime(
        string="Finance Approved On", copy=False, readonly=True
    )

    can_approve_director = fields.Boolean(compute="_compute_can_approve_director")

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.approve_director",
                "name": _lt("Approve (Finance Director)"),
                "kind": "act",
                "group": FINANCE_DIRECTOR_GROUP,
                "sequence": 20,
                "module": "disbursement_approver_director",
            }
        ]

    @api.depends("state")
    @api.depends_context("uid")
    def _compute_can_approve_director(self):
        for rec in self:
            rec.can_approve_director = rec._disbursement_act_offered(
                "disbursement.approve_director"
            )

    def action_approve_finance(self):
        """The act: record the Finance Director's sign-off. Nothing downstream
        fires from it; the budget has its own act."""
        for rec in self:
            rec._disbursement_check_act("disbursement.approve_director")
            rec.finance_approver_id = self.env.user
            rec.finance_approve_date = fields.Datetime.now()
            rec._stamp_signature("finance_approve")
            rec._disbursement_act_done("disbursement.approve_director")
        return True

    def action_draft(self):
        res = super().action_draft()
        self.filtered("finance_approver_id").write(
            {"finance_approver_id": False, "finance_approve_date": False}
        )
        return res
