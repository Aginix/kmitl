# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class BudgetMove(models.Model):
    _inherit = "budget.move"

    def _recompute_project_amounts(self):
        """After posting, cancelling, or resetting a budget.move, recompute
        budget_amount for any kmitl.project whose analytic account appears in
        the affected lines, then auto-re-sync their commitments if pre-spending.
        Runs sudo because the poster may not hold kmitl.project read/write access."""
        project_analytic_ids = self.mapped("line_ids.kmitl_project_analytic_id").ids
        if not project_analytic_ids:
            return
        projects = self.env["kmitl.project"].sudo().search(
            [("analytic_account_id", "in", project_analytic_ids)]
        )
        if not projects:
            return
        projects._compute_budget_amount()
        for project in projects:
            project._auto_resync_commitment()

    def action_post(self):
        res = super().action_post()
        self._recompute_project_amounts()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self._recompute_project_amounts()
        return res

    def button_draft(self):
        res = super().button_draft()
        self._recompute_project_amounts()
        return res
