# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class BudgetMove(models.Model):
    _inherit = "budget.move"

    def _recompute_project_amounts(self):
        """After posting, cancelling, or resetting a budget.move, recompute
        budget_amount for any kmitl.project whose analytic account appears in
        the affected lines. A commitment's event moves only post usage buckets,
        which never change budget_amount, so they are skipped; money moved onto
        a reserved project tops its reservation up in the transfer itself
        (budget ADR-0016). Runs sudo because the poster may not hold
        kmitl.project read/write access."""
        moves = self.filtered(lambda m: not m.commitment_id)
        project_analytic_ids = moves.mapped("line_ids.kmitl_project_analytic_id").ids
        if not project_analytic_ids:
            return
        self.env["kmitl.project"].sudo().search(
            [("analytic_account_id", "in", project_analytic_ids)]
        )._compute_budget_amount()

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
