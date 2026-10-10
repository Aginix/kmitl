# -*- coding: utf-8 -*-
import logging

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, formatLang

_logger = logging.getLogger(__name__)


class BudgetMove(models.Model):
    _inherit = "budget.move"

    def _allocation_projects(self):
        """Projects whose ``kmitl_project`` tag these moves carry. A
        commitment's event moves only post usage buckets, which never change
        budget_amount, so they are skipped."""
        project_analytic_ids = (
            self.filtered(lambda m: not m.commitment_id)
            .mapped("line_ids.kmitl_project_analytic_id")
            .ids
        )
        if not project_analytic_ids:
            return self.env["kmitl.project"]
        return (
            self.env["kmitl.project"]
            .sudo()
            .search([("analytic_account_id", "in", project_analytic_ids)])
        )

    def _recompute_project_amounts(self):
        """After posting, cancelling, or resetting a budget.move, recompute
        budget_amount for any kmitl.project whose analytic account appears in
        the affected lines. Runs sudo because the poster may not hold
        kmitl.project read/write access."""
        self._allocation_projects()._compute_budget_amount()

    def _top_up_project_reservations(self, before):
        """Money allocated onto a reserved project tops its reservation up by
        the same amount (budget ADR-0016, Q5). A budget transfer already does it
        inside its own move (``budget_transfer``), so only what this move did
        not top up itself is posted here — as a reserve event sourced from the
        move, undone again when the move is cancelled or reset."""
        self.ensure_one()
        for project, previous in before.items():
            commitment = project.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial", "done")
            ).sorted("id")[:1]
            if not commitment:
                continue
            topped = -sum(
                self.line_ids.filtered(
                    lambda l, c=commitment: l.commitment_id == c
                    and l.move_type == "reserve"
                ).mapped("balance")
            )
            # What this move brought in, net of what it topped up itself — but
            # never past budget_amount: money the reservation already covers
            # (e.g. an allocation reset and re-posted) is not reserved twice.
            gap = min(
                project.budget_amount - previous - topped,
                project.budget_amount - commitment.amount,
            )
            rounding = commitment.currency_id.rounding or 0.01
            if float_compare(gap, 0.0, precision_rounding=rounding) <= 0:
                continue
            commitment = commitment.sudo()
            commitment.with_context(budget_ledger_posting=True).amount += gap
            commitment._post_budget_event(
                "reserve",
                gap,
                source=self,
                name=_("เพิ่มจองจากการจัดสรรงบ %s") % self.display_name,
                date=self.date,
            )

    def _release_project_top_ups(self):
        """Undo the reservation top-ups these moves caused before they leave
        ``posted``; blocked once a reservation no longer has the topped-up
        amount free (it has been obligated or spent)."""
        events = (
            self.env["budget.commitment.line"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", self.filtered(lambda m: m.state == "posted").ids),
                    ("move_type", "=", "reserve"),
                    ("state", "=", "posted"),
                ]
            )
        )
        for event in events:
            commitment = event.commitment_id
            rounding = commitment.currency_id.rounding or 0.01
            if (
                float_compare(
                    event.amount,
                    commitment._ledger_unobligated(event.account_id),
                    precision_rounding=rounding,
                )
                > 0
            ):
                raise UserError(
                    _(
                        "Cannot undo this budget allocation: reservation %(name)s "
                        "has already obligated or spent part of the %(amount)s "
                        "it received from it."
                    )
                    % {
                        "name": commitment.display_name,
                        "amount": formatLang(
                            self.env, event.amount, currency_obj=commitment.currency_id
                        ),
                    }
                )
            event.action_cancel()
            commitment.with_context(budget_ledger_posting=True).amount -= event.amount

    def action_post(self):
        if not self._allocation_projects():
            return super().action_post()
        # Move by move, so each top-up is sourced from the move that caused it.
        res = True
        for move in self:
            before = {
                project: project.budget_amount
                for project in move._allocation_projects()
            }
            res = super(BudgetMove, move).action_post()
            move._recompute_project_amounts()
            move._top_up_project_reservations(before)
        return res

    def button_cancel(self):
        self._release_project_top_ups()
        res = super().button_cancel()
        self._recompute_project_amounts()
        return res

    def button_draft(self):
        self._release_project_top_ups()
        res = super().button_draft()
        self._recompute_project_amounts()
        return res

    def unlink(self):
        projects = self._allocation_projects()
        self._release_project_top_ups()
        res = super().unlink()
        projects.exists()._compute_budget_amount()
        return res
