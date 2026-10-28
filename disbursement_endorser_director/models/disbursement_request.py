# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _lt, api, fields, models

FINANCE_DIRECTOR_GROUP = "disbursement.group_disbursement_finance_director"


class DisbursementRequest(models.Model):
    """The ผอ.กองคลัง act: the Finance Division Director endorses (เห็นชอบ); the
    Director holds no authority to approve.

    Independent of the validate act: a request that was never validated can be
    endorsed here."""

    _inherit = "disbursement.request"

    finance_endorser_id = fields.Many2one(
        "res.users", string="Endorsed by Finance Director", copy=False, readonly=True
    )
    finance_endorse_date = fields.Datetime(
        string="Finance Endorsed On", copy=False, readonly=True
    )

    can_endorse_director = fields.Boolean(
        string="Can Endorse (Finance Director)",
        compute="_compute_can_endorse_director",
    )

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.endorse_director",
                "name": _lt("Endorse (Finance Director)"),
                "kind": "act",
                "group": FINANCE_DIRECTOR_GROUP,
                "sequence": 20,
                "module": "disbursement_endorser_director",
            }
        ]

    @api.depends("state", "finance_endorser_id")
    @api.depends_context("uid")
    def _compute_can_endorse_director(self):
        """The button waits for a request the Director has not endorsed yet (a
        reset to draft clears the stamp)."""
        for rec in self:
            rec.can_endorse_director = (
                not rec.finance_endorser_id
                and rec._disbursement_act_offered("disbursement.endorse_director")
            )

    def action_endorse_finance(self):
        """The act: record the Finance Director's endorsement. Nothing downstream
        fires from it; the budget has its own act."""
        for rec in self:
            rec._disbursement_check_act("disbursement.endorse_director")
            rec.finance_endorser_id = self.env.user
            rec.finance_endorse_date = fields.Datetime.now()
            rec._stamp_signature("finance_approve")
            rec._disbursement_act_done("disbursement.endorse_director")
        return True

    def action_draft(self):
        res = super().action_draft()
        self.filtered("finance_endorser_id").write(
            {"finance_endorser_id": False, "finance_endorse_date": False}
        )
        return res
