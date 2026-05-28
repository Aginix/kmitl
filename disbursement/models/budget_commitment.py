# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    disbursement_request_ids = fields.One2many(
        string="Disbursement Requests",
        comodel_name="disbursement.request",
        inverse_name="budget_commitment_id",
        copy=False,
    )

    disbursement_request_count = fields.Integer(
        compute="_compute_disbursement_request_count",
    )

    @api.depends("disbursement_request_ids")
    def _compute_disbursement_request_count(self):
        for rec in self:
            rec.disbursement_request_count = len(rec.disbursement_request_ids)

    def action_view_disbursement_requests(self):
        self.ensure_one()
        action = {
            "name": _("Disbursement Requests"),
            "res_model": "disbursement.request",
            "type": "ir.actions.act_window",
        }
        if len(self.disbursement_request_ids) == 1:
            action.update({
                "view_mode": "form",
                "res_id": self.disbursement_request_ids.id,
            })
        else:
            action.update({
                "view_mode": "tree,form",
                "domain": [("id", "in", self.disbursement_request_ids.ids)],
            })
        return action
