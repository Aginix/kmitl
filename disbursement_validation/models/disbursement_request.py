# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _lt, api, fields, models


class DisbursementRequest(models.Model):
    """The ตรวจสอบ act: an officer validates a signed request."""

    _inherit = "disbursement.request"

    # Who actually pressed Validate. Distinct from ``assigned_to``
    # (disbursement_assignment_kmitl), which records who was *assigned* the
    # verification and may be a different person once takeover is allowed.
    verifier_id = fields.Many2one(
        "res.users", string="Verified By", copy=False, readonly=True
    )
    verify_date = fields.Datetime(string="Verified On", copy=False, readonly=True)

    can_validate = fields.Boolean(compute="_compute_can_validate")

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.validate",
                "name": _lt("Validate"),
                "kind": "act",
                "group": "disbursement.group_disbursement_officer",
                "sequence": 10,
                "module": "disbursement_validation",
            }
        ]

    @api.depends("state")
    @api.depends_context("uid")
    def _compute_can_validate(self):
        for rec in self:
            rec.can_validate = rec._disbursement_act_offered("disbursement.validate")

    def action_validate(self):
        """The act: the officer validates the request. It changes no state, so
        doing it again only re-stamps (the previous signature row is archived)."""
        for rec in self:
            rec._disbursement_check_act("disbursement.validate")
            rec.verifier_id = self.env.user
            rec.verify_date = fields.Datetime.now()
            rec._stamp_signature("verify")
            rec._resolve_source_correction_todos()
            rec._disbursement_act_done("disbursement.validate")
        return True

    def action_draft(self):
        res = super().action_draft()
        self.filtered("verifier_id").write({"verifier_id": False, "verify_date": False})
        return res
