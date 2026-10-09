import logging

from odoo import Command, _, api, fields, models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    """A commitment line is an event: a command that posts to the budget ledger
    (ADR-0016). It is never summed for a figure."""

    _inherit = "budget.commitment.line"

    budget_move_line_id = fields.Many2one(
        comodel_name="budget.move.line",
        string="Budget Ledger Line",
        readonly=True,
        index=True,
        copy=False,
        ondelete="set null",
        help="The ledger line that posted this event. For a top-up it sits "
        "inside the budget transfer's move.",
    )

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------
    def _post_budget_moves(self):
        """Post each new event of an active reservation to the ledger.

        A draft reservation's events wait for ``action_reserve``; a top-up is
        posted by the transfer itself (``budget_ledger_external``).
        """
        if self.env.context.get("budget_ledger_external"):
            return
        to_post = self.filtered(
            lambda l: l.state == "posted"
            and not l.budget_move_line_id
            and l.commitment_id.state != "draft"
        ).sorted("id")
        for line in to_post:
            line._post_ledger_move()
        to_post._check_commitment_limits()

    def _post_ledger_move(self):
        """Post this event as its own ``budget.move`` (ADR-0016, Q2)."""
        self.ensure_one()
        move = (
            self.env["budget.move"]
            .sudo()
            .with_context(budget_ledger_posting=True)
            .create(self._prepare_ledger_move_vals())
        )
        move.action_review()
        move.action_post()
        self.write(
            {
                "budget_move_id": move.id,
                "budget_move_line_id": move.line_ids.filtered(
                    lambda l: not l.is_liquidation
                )[:1].id,
            }
        )
        return move

    def _prepare_ledger_move_vals(self):
        self.ensure_one()
        commitment = self.commitment_id
        vals = {
            "date": self.date,
            "move_type": self.move_type,
            "budget_type": "expense",
            "ref": commitment.name,
            "note": self.name,
            "account_fiscal_year_id": commitment.account_fiscal_year_id.id,
            "department_analytic_id": self.department_analytic_id.id,
            "source_analytic_id": self.source_analytic_id.id,
            "company_id": commitment.company_id.id,
            "currency_id": commitment.currency_id.id,
            "commitment_id": commitment.id,
            "commitment_line_id": self.id,
            "res_model": self.res_model,
            "res_id": self.res_id,
            "line_ids": [
                Command.create(vals) for vals in self._prepare_ledger_line_vals()
            ],
        }
        move_fields = self.env["budget.move"]._fields
        if "operating_unit_id" in move_fields and "operating_unit_id" in commitment._fields:
            vals["operating_unit_id"] = commitment.operating_unit_id.id
        return vals

    def _prepare_ledger_line_vals(self):
        self.ensure_one()
        distribution = self._ledger_distribution()
        return [
            {
                "account_id": self.account_id.id,
                "balance": balance,
                "analytic_distribution": distribution,
                "move_type": bucket,
                "commitment_id": self.commitment_id.id,
                "commitment_line_id": self.id,
                "is_liquidation": is_liquidation,
                "is_return": self.is_return and not is_liquidation,
            }
            for bucket, balance, is_liquidation in self._ledger_entries()
        ]

    def _ledger_entries(self):
        """[(bucket, balance, is_liquidation)] for this event (ADR-0016, Q2).

        reserve X  → reserve −X
        obligate X → obligate −X, reserve +X
        consume X  → consume −X, obligate +X — or reserve +X when nothing is
                     obligated (so an over-consume of an obligation is still
                     blocked by the limits, as before)
        A negative amount (a return, a de-obligation, a refund) mirrors it.
        """
        self.ensure_one()
        amount = self.amount
        if self.move_type == "reserve":
            return [("reserve", -amount, False)]
        if self.move_type == "obligate":
            return [("obligate", -amount, False), ("reserve", amount, True)]
        currency = self.currency_id or self.env.company.currency_id
        obligated = self.commitment_id.available_to_consume
        bucket = (
            "reserve"
            if amount > 0 and currency.compare_amounts(obligated, 0.0) <= 0
            else "obligate"
        )
        return [("consume", -amount, False), (bucket, amount, True)]

    def _ledger_distribution(self):
        """The event's full coordinate: its own dimensions plus the header's
        for every plan the line does not carry (a host's reserve line often
        carries only activity + fund; the header carries the rest)."""
        self.ensure_one()
        Analytic = self.env["account.analytic.account"]
        distribution = dict(self.analytic_distribution or {})
        plans = {
            account.root_plan_id.code
            for account in Analytic.browse([int(key) for key in distribution]).exists()
        }
        for key, percentage in (self.commitment_id.analytic_distribution or {}).items():
            account = Analytic.browse(int(key)).exists()
            if account and account.root_plan_id.code not in plans:
                distribution[key] = percentage
        return distribution or False

    # ------------------------------------------------------------------
    # Limits, read from the ledger (ADR-0016, Q7)
    # ------------------------------------------------------------------
    @api.constrains("amount", "move_type", "state")
    def _check_commitment_limits(self):
        self.mapped("commitment_id")._check_ledger_limits()

    # ------------------------------------------------------------------
    # Cancellation (ADR-0016, Q6)
    # ------------------------------------------------------------------
    def action_cancel(self):
        """Cancel the events' own moves; reverse a top-up living in a transfer's
        move with a new move instead of touching the transfer."""
        to_cancel = self.filtered(lambda l: l.state != "cancel")
        to_cancel.budget_move_id.filtered(lambda m: m.state != "cancel").sudo().button_cancel()
        foreign = to_cancel.filtered(
            lambda l: l.budget_move_line_id and not l.budget_move_id
        )
        res = super().action_cancel()
        for line in foreign:
            line._post_ledger_reversal()
        to_cancel._check_commitment_limits()
        return res

    def _post_ledger_reversal(self):
        """Post a move negating this event's posted ledger lines."""
        self.ensure_one()
        lines = self.env["budget.move.line"].sudo().search(
            [("commitment_line_id", "=", self.id), ("parent_state", "=", "posted")]
        )
        if not lines:
            return False
        commitment = self.commitment_id
        vals = dict(
            self._prepare_ledger_move_vals(),
            date=fields.Date.context_today(self),
            note=_("ยกเลิก: %s") % (self.name or ""),
            line_ids=[
                Command.create(
                    {
                        "account_id": line.account_id.id,
                        "balance": -line.balance,
                        "analytic_distribution": line.analytic_distribution,
                        "move_type": line.move_type,
                        "commitment_id": commitment.id,
                        "commitment_line_id": self.id,
                        "is_liquidation": True,
                    }
                )
                for line in lines
            ],
        )
        move = (
            self.env["budget.move"]
            .sudo()
            .with_context(budget_ledger_posting=True)
            .create(vals)
        )
        move.action_review()
        move.action_post()
        return move

    # ------------------------------------------------------------------
    # Back-fill (ADR-0016, Q11)
    # ------------------------------------------------------------------
    def _ledger_backfill_post(self):
        """Post a historical event. A consume that already has its posted
        consume move keeps it (and its number): the move gains the
        liquidation lines and its consume line the event's full coordinate."""
        self.ensure_one()
        move = self.budget_move_id
        if not (self.move_type == "consume" and move and move.state == "posted"):
            return self._post_ledger_move()
        Line = self.env["budget.move.line"].with_context(budget_ledger_posting=True)
        distribution = self._ledger_distribution()
        entries = self._ledger_entries()
        primary = move.line_ids.filtered(lambda l: l.move_type == "consume")[:1]
        primary_vals = {
            "commitment_id": self.commitment_id.id,
            "commitment_line_id": self.id,
            "analytic_distribution": distribution,
        }
        if primary:
            primary.with_context(budget_ledger_posting=True).write(primary_vals)
        else:
            bucket, balance, _liq = entries[0]
            primary = Line.create(
                dict(
                    primary_vals,
                    move_id=move.id,
                    account_id=self.account_id.id,
                    balance=balance,
                    move_type=bucket,
                )
            )
        if float_compare(
            -primary.balance,
            self.amount,
            precision_rounding=self.currency_id.rounding or 0.01,
        ):
            _logger.warning(
                "budget_ledger back-fill: consume move %s (%.2f) differs from "
                "its event %s (%.2f)",
                move.name,
                -primary.balance,
                self.id,
                self.amount,
            )
        for bucket, balance, is_liquidation in entries[1:]:
            Line.create(
                {
                    "move_id": move.id,
                    "account_id": self.account_id.id,
                    "balance": balance,
                    "analytic_distribution": distribution,
                    "move_type": bucket,
                    "commitment_id": self.commitment_id.id,
                    "commitment_line_id": self.id,
                    "is_liquidation": is_liquidation,
                }
            )
        move.with_context(budget_ledger_posting=True).write(
            {
                "commitment_id": self.commitment_id.id,
                "commitment_line_id": self.id,
                "res_model": self.res_model,
                "res_id": self.res_id,
            }
        )
        self.budget_move_line_id = primary
        return move
