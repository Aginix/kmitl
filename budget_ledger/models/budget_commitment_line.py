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
            lambda line: (
                line.state == "posted"
                and not line.budget_move_line_id
                and line.commitment_id.state != "draft"
            )
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
                    lambda line: not line.is_liquidation
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
        if (
            "operating_unit_id" in move_fields
            and "operating_unit_id" in commitment._fields
        ):
            vals["operating_unit_id"] = commitment.operating_unit_id.id
        return vals

    def _prepare_ledger_line_vals(self):
        self.ensure_one()
        distribution = self._ledger_distribution()
        return [
            {
                "account_id": account.id,
                "balance": balance,
                "analytic_distribution": distribution,
                "move_type": bucket,
                "commitment_id": self.commitment_id.id,
                "commitment_line_id": self.id,
                "is_liquidation": is_liquidation,
                "is_return": self.is_return and not is_liquidation,
            }
            for account, bucket, balance, is_liquidation in self._ledger_entries()
        ]

    def _ledger_entries(self):
        """[(budget code, bucket, balance, is_liquidation)] for this event
        (ADR-0016, Q2).

        reserve X  → reserve −X
        obligate X → obligate −X, reserve +X
        consume X  → consume −X, obligate +X — or reserve +X when the source
                     document obligated nothing (so an over-consume of an
                     obligation is still blocked by the limits, as before, and
                     a document never liquidates another document's obligation
                     on a shared reservation)
        A negative amount (a return, a de-obligation, a refund) mirrors it; a
        refund goes back to the bucket the source's consumes liquidated.

        On a ถัวจ่าย reservation every event but a reserve is split over its
        budget codes in order (ADR-0017): obligate/consume draw the primary
        code first, a return/de-obligation/refund gives back the last first.
        """
        self.ensure_one()
        amount = self.amount
        if self.move_type == "reserve" and not self.is_return:
            return [(self.account_id, "reserve", -amount, False)]
        if self.move_type == "reserve":
            parts = self._ledger_split(
                -amount, self._ledger_code_held("reserve", own=False), reverse=True
            )
            return [(account, "reserve", part, False) for account, part in parts]
        if self.move_type == "obligate":
            if amount >= 0:
                parts = self._ledger_split(
                    amount, self._ledger_code_held("reserve", own=False)
                )
            else:
                parts = self._ledger_split(
                    -amount, self._ledger_code_held("obligate"), reverse=True, sign=-1
                )
            return self._ledger_pairs(parts, "obligate", "reserve")
        currency = self.currency_id or self.env.company.currency_id
        if amount > 0:
            obligated = sum(self._ledger_code_held("obligate").values())
            from_reserve = currency.compare_amounts(obligated, 0.0) <= 0
            bucket = "reserve" if from_reserve else "obligate"
            parts = self._ledger_split(
                amount, self._ledger_code_held(bucket, own=not from_reserve)
            )
        else:
            liquidated = -sum(
                self._ledger_code_held("reserve", liquidated_by="consume").values()
            )
            from_reserve = currency.compare_amounts(liquidated, -amount) >= 0
            bucket = "reserve" if from_reserve else "obligate"
            parts = self._ledger_split(
                -amount, self._ledger_code_held("consume"), reverse=True, sign=-1
            )
        return self._ledger_pairs(parts, "consume", bucket)

    @staticmethod
    def _ledger_pairs(parts, bucket, liquidated_bucket):
        """Per code: the event's own line and the line it liquidates."""
        entries = []
        for account, part in parts:
            entries.append((account, bucket, -part, False))
            entries.append((account, liquidated_bucket, part, True))
        return entries

    def _ledger_split(self, amount, held, reverse=False, sign=1):
        """[(budget code, signed part)] spreading ``amount`` (> 0) over the
        reservation's codes in liquidation order — reversed when giving back —
        each up to what ``held`` says it holds. What no code can take stays on
        the primary code, so the reservation's limits still catch it."""
        self.ensure_one()
        currency = self.currency_id or self.env.company.currency_id
        codes = list(self.commitment_id._ledger_codes()) or [self.account_id]
        parts = {}
        left = amount
        for account in reversed(codes) if reverse else codes:
            take = min(left, max(held.get(account, 0.0), 0.0))
            if currency.compare_amounts(take, 0.0) > 0:
                parts[account] = take
                left -= take
        if currency.compare_amounts(left, 0.0) > 0 or not parts:
            parts[codes[0]] = parts.get(codes[0], 0.0) + left
        return [(account, sign * part) for account, part in parts.items()]

    def _ledger_code_held(self, bucket, own=True, liquidated_by=None):
        """{budget code: amount held in ``bucket``} (−Σ posted balance) on this
        event's reservation — of this event's source document only when
        ``own`` and the event has one. ``liquidated_by`` keeps only the
        liquidation lines of that event type."""
        self.ensure_one()
        domain = [
            ("commitment_id", "=", self.commitment_id.id),
            ("parent_state", "=", "posted"),
            ("move_type", "=", bucket),
        ]
        if own and self.res_model:
            domain += [
                ("commitment_line_id.res_model", "=", self.res_model),
                ("commitment_line_id.res_id", "=", self.res_id),
            ]
        if liquidated_by:
            domain += [
                ("is_liquidation", "=", True),
                ("commitment_line_id.move_type", "=", liquidated_by),
            ]
        held = {}
        for line in self.env["budget.move.line"].sudo().search(domain):
            held[line.account_id] = held.get(line.account_id, 0.0) - line.balance
        return held

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
        to_cancel = self.filtered(lambda line: line.state != "cancel")
        to_cancel.budget_move_id.filtered(
            lambda m: m.state != "cancel"
        ).sudo().button_cancel()
        foreign = to_cancel.filtered(
            lambda line: line.budget_move_line_id and not line.budget_move_id
        )
        res = super().action_cancel()
        for line in foreign:
            line._post_ledger_reversal()
        to_cancel._check_commitment_limits()
        return res

    def _post_ledger_reversal(self):
        """Post a move negating this event's posted ledger lines."""
        self.ensure_one()
        lines = (
            self.env["budget.move.line"]
            .sudo()
            .search(
                [("commitment_line_id", "=", self.id), ("parent_state", "=", "posted")]
            )
        )
        if not lines:
            return False
        commitment = self.commitment_id
        # The header is not stamped as the event (nor its source document):
        # the reversal undoes an event, it is not one.
        vals = dict(
            self._prepare_ledger_move_vals(),
            commitment_line_id=False,
            res_model=False,
            res_id=False,
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
        primary = move.line_ids.filtered(lambda line: line.move_type == "consume")[:1]
        if primary and float_compare(
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
        account, bucket, balance, _liq = entries[0]
        primary_vals = {
            "commitment_id": self.commitment_id.id,
            "commitment_line_id": self.id,
            "analytic_distribution": distribution,
        }
        # A ถัวจ่าย consume split over several codes (ADR-0017) re-cuts the
        # old single consume line into the first code's share.
        if not primary or len(entries) > 2:
            primary_vals.update(account_id=account.id, balance=balance)
        if primary:
            primary.with_context(budget_ledger_posting=True).write(primary_vals)
        else:
            primary = Line.create(dict(primary_vals, move_id=move.id, move_type=bucket))
        for account, bucket, balance, is_liquidation in entries[1:]:
            Line.create(
                {
                    "move_id": move.id,
                    "account_id": account.id,
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
