# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    disbursement_request_ids = fields.One2many(
        comodel_name="disbursement.request",
        inverse_name="kmitl_project_id",
        string="ใบขอเบิก",
    )
    disbursement_request_count = fields.Integer(
        compute="_compute_disbursement_request_count",
    )
    can_create_disbursement = fields.Boolean(
        compute="_compute_can_create_disbursement",
    )

    @api.depends("disbursement_request_ids")
    def _compute_disbursement_request_count(self):
        for rec in self:
            rec.disbursement_request_count = len(rec.disbursement_request_ids)

    @api.depends(
        "state",
        "budget_amount",
        "budget_commitment_ids.state",
        "budget_commitment_ids.total_consumed",
    )
    def _compute_can_create_disbursement(self):
        """Non-purchase project expenses are disbursed directly, without an
        agx_approval in between: the button shows once the project is approved and
        executing (``in_progress`` with an active commitment — kmitl_project
        ADR-0005) while any reserved budget is still unspent."""
        for rec in self:
            has_commitment = bool(
                rec.budget_commitment_ids.filtered(
                    lambda c: c.state in ("reserved", "partial")
                )
            )
            rec.can_create_disbursement = (
                rec.state == "in_progress"
                and has_commitment
                and rec.budget_remaining > 0
            )

    def action_create_disbursement_request(self):
        """Create a disbursement request (ใบขอเบิก) from the project for a
        non-purchase expense, pre-filled from the project's reserved-budget
        context. The DR draws the project's shared commitment (capped by the
        reservation at approval); the user fills in the payee lines and submits —
        no agx_approval step in between."""
        self.ensure_one()
        commitment = self.budget_commitment_ids.filtered(
            lambda c: c.state in ("reserved", "partial")
        )[:1]
        if self.state != "in_progress" or not commitment:
            raise UserError(
                _("สร้างใบขอเบิกได้เฉพาะโครงการที่ได้รับอนุมัติและกำลังดำเนินการเท่านั้น")
            )
        if self.budget_remaining <= 0:
            raise UserError(_("งบประมาณคงเหลือของโครงการไม่เพียงพอสำหรับการเบิกจ่าย"))
        return {
            "type": "ir.actions.act_window",
            "name": _("สร้างใบขอเบิกจากโครงการ"),
            "res_model": "disbursement.request",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_reference": "kmitl.project,%d" % self.id,
                "default_budget_commitment_id": commitment.id,
                "default_budget_account_id": self.budget_account_id.id,
                "default_analytic_distribution": self.analytic_distribution,
            },
        }

    def action_view_disbursement_requests(self):
        self.ensure_one()
        action = {
            "name": _("ใบขอเบิก"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "domain": [("id", "in", self.disbursement_request_ids.ids)],
        }
        if len(self.disbursement_request_ids) == 1:
            action.update(
                {"view_mode": "form", "res_id": self.disbursement_request_ids.id}
            )
        else:
            action["view_mode"] = "tree,form"
        return action
