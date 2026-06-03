# -*- coding: utf-8 -*-
from odoo import _, fields, models


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
