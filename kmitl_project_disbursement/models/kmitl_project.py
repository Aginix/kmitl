# -*- coding: utf-8 -*-
from odoo import _, fields, models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    disbursement_count = fields.Integer(
        compute="_compute_disbursement_count",
        string="Disbursement Count",
    )

    def _compute_disbursement_count(self):
        DR = self.env["disbursement.request"]
        for rec in self:
            rec.disbursement_count = (
                DR.search_count(rec._disbursement_domain())
                if rec.analytic_account_id
                else 0
            )

    def _disbursement_domain(self):
        """Disbursements raised under this project — those carrying the project's
        own ``kmitl_project`` analytic account (unique per project, minted once)."""
        self.ensure_one()
        return [("kmitl_project_analytic_id", "=", self.analytic_account_id.id)]

    def action_open_disbursements(self):
        self.ensure_one()
        return {
            "name": _("การเบิกจ่าย"),
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "tree,form",
            "domain": self._disbursement_domain(),
        }
