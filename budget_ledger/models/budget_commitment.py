import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

_BUCKETS = ("reserve", "obligate", "consume")
_TOTAL_FIELDS = (
    "total_reserved",
    "total_obligated",
    "total_consumed",
    "available_to_obligate",
    "available_to_consume",
    "consumed_amount",
    "remaining_amount",
)


class BudgetCommitment(models.Model):
    """The reservation as a sub-ledger of the budget ledger (ADR-0016).

    Its figures are the negated Σ balance of its posted ledger lines per bucket:
    b = reserve, c = obligate, d = consume. ``available_to_obligate`` = b,
    ``available_to_consume`` = c, ``total_consumed`` = d, ``total_obligated`` =
    c + d and ``total_reserved`` = b + c + d. Its lines are the event log and
    are never summed.
    """

    _inherit = "budget.commitment"

    ledger_line_ids = fields.One2many(
        comodel_name="budget.move.line",
        inverse_name="commitment_id",
        string="บัญชีงบประมาณ",
        readonly=True,
    )

    @api.depends(
        "ledger_line_ids.balance",
        "ledger_line_ids.move_type",
        "ledger_line_ids.parent_state",
        "amount",
    )
    def _compute_line_totals(self):
        for record in self:
            buckets = record._ledger_buckets()
            reserve, obligate, consume = (-buckets[b] for b in _BUCKETS)
            record.available_to_obligate = reserve
            record.available_to_consume = obligate
            record.total_consumed = consume
            record.total_obligated = obligate + consume
            record.total_reserved = reserve + obligate + consume
            # Legacy compat
            record.consumed_amount = consume
            record.remaining_amount = record.amount - consume

    def _ledger_buckets(self):
        """{bucket: Σ posted balance} of this reservation's ledger lines."""
        self.ensure_one()
        currency = self.currency_id or self.env.company.currency_id
        buckets = dict.fromkeys(_BUCKETS, 0.0)
        for line in self.ledger_line_ids:
            if line.parent_state == "posted" and line.move_type in buckets:
                buckets[line.move_type] += line.balance
        return {key: currency.round(value) for key, value in buckets.items()}

    def action_reserve(self):
        """Reserving posts the reserve events written while draft.

        One reservation at a time: the pool only nets a reservation once its
        events are posted, so the next one in a batch must be checked after.
        """
        res = None
        for record in self:
            res = super(BudgetCommitment, record).action_reserve()
            record.line_ids.filtered(
                lambda line: line.state == "posted"
            )._post_budget_moves()
        return res

    @api.constrains("amount", "state")
    def _check_positive_amount(self):
        """A transfer may release a reservation's whole unobligated remainder
        (ADR-0016, Q5): its cap then rests at 0 — an empty reservation a later
        transfer can top up again — so a zero cap is allowed while that release
        posts, or once nothing is reserved on it."""
        posting = self.env.context.get("budget_ledger_posting")
        empty = self.filtered(
            lambda c: (
                c.state != "draft"
                and not c.amount
                and (
                    posting
                    or (c.currency_id or self.env.company.currency_id).is_zero(
                        c.total_reserved
                    )
                )
            )
        )
        return super(BudgetCommitment, self - empty)._check_positive_amount()

    def _availability_distribution(self):
        """Pool tags are pinned on both sides of the engine (ADR-0016, Q3), so a
        reservation is checked at its full coordinate, tag included."""
        self.ensure_one()
        return dict(self.analytic_distribution or {})

    def _budget_event_lines(self, source=None, move_types=None):
        """Posted events, read from the ledger: each live event owns one posted
        primary ledger line — in its own move, or inside a transfer's move for
        a top-up/release."""
        self.ensure_one()
        domain = [
            ("commitment_id", "=", self.id),
            ("parent_state", "=", "posted"),
            ("is_liquidation", "=", False),
            ("commitment_line_id.state", "=", "posted"),
        ]
        if source:
            domain += [
                ("commitment_line_id.res_model", "=", source._name),
                ("commitment_line_id.res_id", "=", source.id),
            ]
        if move_types:
            domain.append(("commitment_line_id.move_type", "in", list(move_types)))
        lines = self.env["budget.move.line"].sudo().search(domain)
        return lines.commitment_line_id.with_env(self.env)

    def _check_ledger_limits(self):
        """reserved ≤ cap, and no bucket overdrawn — read from the ledger."""
        for commitment in self:
            rounding = commitment.currency_id.rounding or 0.01

            def over(a, b):
                return float_compare(a, b, precision_rounding=rounding) > 0

            reserved = commitment.total_reserved
            obligated = commitment.total_obligated
            consumed = commitment.total_consumed
            if commitment.amount and over(reserved, commitment.amount):
                raise ValidationError(
                    _(
                        "Total reserved (%(reserved).2f) exceeds commitment cap (%(cap).2f)"
                    )
                    % {"reserved": reserved, "cap": commitment.amount}
                )
            if over(obligated, reserved):
                raise ValidationError(
                    _(
                        "Total obligated (%(obligated).2f) exceeds total reserved (%(reserved).2f)"
                    )
                    % {"obligated": obligated, "reserved": reserved}
                )
            if over(consumed, obligated):
                raise ValidationError(
                    _(
                        "Total consumed (%(consumed).2f) exceeds total obligated (%(obligated).2f)"
                    )
                    % {"consumed": consumed, "obligated": obligated}
                )
            for label, value in (
                (_("reserved"), reserved),
                (_("obligated"), obligated),
                (_("consumed"), consumed),
            ):
                if over(0.0, value):
                    raise ValidationError(
                        _("Total %(label)s cannot be negative (%(value).2f).")
                        % {"label": label, "value": value}
                    )

    def action_view_budget_moves(self):
        """Every move carrying this reservation's ledger lines — its own event
        moves and the transfers that topped it up."""
        action = super().action_view_budget_moves()
        action["domain"] = [("id", "in", self.ledger_line_ids.move_id.ids)]
        return action

    # ------------------------------------------------------------------
    # Transfer top-up / release (ADR-0016, Q5/Q6)
    # ------------------------------------------------------------------
    def _ledger_post_transfer_event(self, transfer_line, amount):
        """Add a ``reserve`` event of ``amount`` (positive = top-up, negative =
        release) as a line inside the transfer's own move, and move the cap.

        The transfer's move is posted right after, so no separate event move is
        created (the event is ``budget_ledger_external``).
        """
        self.ensure_one()
        transfer_move = transfer_line.move_id
        source = transfer_move.transfer_ids[:1] or transfer_move
        event = (
            self.env["budget.commitment.line"]
            .sudo()
            .with_context(budget_ledger_external=True)
            .create(
                {
                    "commitment_id": self.id,
                    "move_type": "reserve",
                    "account_id": transfer_line.account_id.id,
                    "analytic_distribution": transfer_line._ledger_coordinate(),
                    "amount": amount,
                    "date": transfer_move.date,
                    "res_model": source._name,
                    "res_id": source.id,
                    "name": (
                        _("เพิ่มจองจากการโอนงบ %s")
                        if amount > 0
                        else _("ปลดจองจากการโอนงบ %s")
                    )
                    % transfer_move.display_name,
                }
            )
        )
        ledger_line = (
            self.env["budget.move.line"]
            .sudo()
            .with_context(budget_ledger_posting=True)
            .create(
                {
                    "move_id": transfer_move.id,
                    "account_id": transfer_line.account_id.id,
                    "balance": -amount,
                    "analytic_distribution": transfer_line._ledger_coordinate(),
                    "move_type": "reserve",
                    "commitment_id": self.id,
                    "commitment_line_id": event.id,
                }
            )
        )
        event.budget_move_line_id = ledger_line
        self.sudo().with_context(budget_ledger_posting=True).amount += amount
        return event

    # ------------------------------------------------------------------
    # Back-fill + reconciliation (ADR-0016, Q11)
    # ------------------------------------------------------------------
    def _ledger_legacy_totals(self):
        """(reserved, obligated, consumed) re-derived from the posted events the
        old way, for reconciliation only — never used as a figure."""
        self.ensure_one()
        sums = dict.fromkeys(_BUCKETS, 0.0)
        for line in self.line_ids.filtered(lambda line: line.state == "posted"):
            sums[line.move_type] += line.amount
        # The old ledger forbade consuming more than obligated; a consume that
        # liquidated the reserve directly counts as obligated too.
        return sums["reserve"], max(sums["obligate"], sums["consume"]), sums["consume"]

    def _ledger_mismatches(self):
        """Reservations whose ledger figures differ from their posted events."""
        mismatched = self.browse()
        for commitment in self:
            rounding = commitment.currency_id.rounding or 0.01
            legacy = commitment._ledger_legacy_totals()
            ledger = (
                commitment.total_reserved,
                commitment.total_obligated,
                commitment.total_consumed,
            )
            if any(
                float_compare(a, b, precision_rounding=rounding)
                for a, b in zip(legacy, ledger)
            ):
                mismatched |= commitment
        return mismatched

    def _ledger_backfill(self):
        """Post the history of every active reservation to the ledger.

        Per reservation, its posted events are posted in date order; an event
        that already has its consume move keeps it and gains the liquidation
        lines. Mismatches are logged and kept in
        ``budget_ledger.backfill_mismatch_commitment_ids`` — the install never
        aborts on them (ADR-0016, Q11).
        """
        everything = self.search([])
        # The stored figures still hold the event-based values; recompute them
        # from the ledger as it fills, so each consume liquidates the right bucket.
        for fname in _TOTAL_FIELDS:
            self.env.add_to_compute(self._fields[fname], everything)
        commitments = everything.filtered(
            lambda c: c.state not in ("draft", "cancel")
        ).sorted("id")
        for commitment in commitments:
            events = commitment.line_ids.filtered(
                lambda line: line.state == "posted" and not line.budget_move_line_id
            ).sorted(lambda line: (line.date, line.id))
            for event in events:
                try:
                    with self.env.cr.savepoint():
                        event._ledger_backfill_post()
                except Exception as err:  # report, never abort the install
                    _logger.warning(
                        "budget_ledger back-fill: event %s of %s not posted: %s",
                        event.id,
                        commitment.display_name,
                        err,
                    )
        for fname in _TOTAL_FIELDS:
            self.env.add_to_compute(self._fields[fname], everything)
        everything.flush_recordset()
        mismatched = commitments._ledger_mismatches()
        if mismatched:
            _logger.warning(
                "budget_ledger back-fill: %d reservation(s) do not reconcile: %s",
                len(mismatched),
                ", ".join(mismatched.mapped("display_name")),
            )
        else:
            _logger.info(
                "budget_ledger back-fill: %d reservation(s) posted and reconciled",
                len(commitments),
            )
        self.env["ir.config_parameter"].sudo().set_param(
            "budget_ledger.backfill_mismatch_commitment_ids",
            json.dumps(mismatched.ids),
        )
        return mismatched
