# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    READONLY_STATES = {
        "reserved": [("readonly", True)],
        "partial": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    kmitl_project_id = fields.Many2one(
        comodel_name="kmitl.project",
        string="โครงการ/กิจกรรม",
        states=READONLY_STATES,
    )

    @api.onchange("kmitl_project_analytic_id")
    def _onchange_kmitl_project_analytic_id(self):
        """Keep ``kmitl_project_id`` in step with the โครงการ/กิจกรรม analytic
        dimension: when the analytic account changes, point the record link at
        the project owning that account (cleared when no project matches)."""
        account = self.kmitl_project_analytic_id
        self.kmitl_project_id = (
            self.env["kmitl.project"].search(
                [("analytic_account_id", "=", account.id)], limit=1
            )
            if account
            else False
        )

    def action_view_kmitl_project(self):
        self.ensure_one()
        if not self.kmitl_project_id:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project",
            "view_mode": "form",
            "res_id": self.kmitl_project_id.id,
            "target": "current",
        }
