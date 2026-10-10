import logging

from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

PROTECTED_FIELDS = {
    "amount",
    "account_id",
    "move_type",
    "analytic_distribution",
    "activity_analytic_id",
    "fund_analytic_id",
}


class BudgetCommitmentLine(models.Model):
    """Budget Commitment Line - Ledger entry for budget operations.

    Each line represents a budget transaction:
    - reserve: จองงบประมาณ (positive = จอง, negative = คืนจอง)
    - obligate: ผูกพันงบประมาณ (positive = ผูกพัน, negative = คืนผูกพัน)
    - consume: ตัดงบประมาณ (positive = ตัดงบ, negative = คืนเงิน)

    Posted lines are immutable — cancel instead of edit/delete.

    A line is an event: a command that posts to the budget ledger
    (``budget.move.line``, ADR-0016). It is never summed for a figure — every
    figure is read from the ledger.
    """

    _name = "budget.commitment.line"
    _description = "Budget Commitment Line"
    _inherit = ["analytic.mixin", "mail.thread"]
    _order = "sequence, id"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Commitment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
    )
    name = fields.Char(string="Description")
    move_type = fields.Selection(
        selection=[
            ("reserve", "จองงบ"),
            ("obligate", "ผูกพัน"),
            ("consume", "ตัดงบ"),
        ],
        string="Type",
        required=True,
        default="reserve",
        tracking=True,
    )
    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
    )
    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
        help="Positive = forward (reserve/obligate/consume), Negative = reversal",
    )
    is_return = fields.Boolean(
        string="ส่งคืนเงินเหลือจ่าย",
        default=False,
        help=(
            "บรรทัดคืนจอง (negative reserve) ที่เกิดจากการส่งคืนเงินเหลือจ่าย "
            "ปลดเงินจองที่ยังไม่ได้ตัดกลับเข้ากระเป๋างบประมาณ โดยไม่ยกเลิก commitment"
        ),
    )
    state = fields.Selection(
        selection=[
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        default="posted",
        tracking=True,
    )

    # Source document reference (e.g. purchase.request, purchase.order)
    res_model = fields.Char(
        string="Source Model",
        index=True,
        readonly=True,
    )
    res_id = fields.Many2oneReference(
        string="Source Document",
        model_field="res_model",
        index=True,
        readonly=True,
    )
    res_name = fields.Char(
        string="Source Name",
        compute="_compute_res_name",
    )

    # The budget.move this event posted (ADR-0016)
    budget_move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Budget Move",
        readonly=True,
        index=True,
        ondelete="set null",
    )
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

    # Analytic convenience fields (line-level: activity + fund only)
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=True,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=True,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "funds": "fund_analytic_id",
    }

    def _inverse_activity_analytic(self):
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_fund_analytic(self):
        for line in self:
            line._update_analytic_distribution("funds")

    # Related from header
    department_analytic_id = fields.Many2one(
        related="commitment_id.department_analytic_id",
        store=True,
        string="ส่วนงาน",
    )
    source_analytic_id = fields.Many2one(
        related="commitment_id.source_analytic_id",
        store=True,
        string="แหล่งเงิน",
    )
    kmitl_project_analytic_id = fields.Many2one(
        related="commitment_id.kmitl_project_analytic_id",
        store=True,
        string="โครงการ/กิจกรรม",
    )
    procurement_plan_analytic_id = fields.Many2one(
        related="commitment_id.procurement_plan_analytic_id",
        store=True,
        string="แผนจัดซื้อจัดจ้าง",
    )
    currency_id = fields.Many2one(related="commitment_id.currency_id")
    company_id = fields.Many2one(
        related="commitment_id.company_id",
        store=True,
    )
    account_fiscal_year_id = fields.Many2one(
        related="commitment_id.account_fiscal_year_id",
        store=True,
        string="ปีงบประมาณ",
    )

    @api.depends("res_model", "res_id")
    def _compute_res_name(self):
        for line in self:
            if line.res_model and line.res_id:
                record = self.env[line.res_model].browse(line.res_id).exists()
                line.res_name = record.display_name if record else False
            else:
                line.res_name = False

    def action_open_source_document(self):
        """Open the source document that created this line."""
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }

    # --- Constraints ---

    @api.constrains("amount", "move_type", "state")
    def _check_commitment_limits(self):
        """reserved ≤ cap, obligated ≤ reserved, consumed ≤ obligated, none
        negative — read from the ledger (ADR-0016, Q7)."""
        self.mapped("commitment_id")._check_ledger_limits()

    @api.constrains("account_id", "move_type", "state")
    def _check_cross_charge(self):
        """A reservation may span >1 budget code only if all are cross-chargeable.

        ถัวจ่าย (ADR 0006): a single reserve line is always allowed; multiple
        reserve lines with *different* budget accounts require every one of
        those accounts to be flagged ``cross_chargeable``.
        """
        for commitment in self.mapped("commitment_id"):
            accounts = commitment.line_ids.filtered(
                lambda l: l.state == "posted" and l.move_type == "reserve"
            ).mapped("account_id")
            if len(accounts) > 1:
                blocked = accounts.filtered(lambda a: not a.cross_chargeable)
                if blocked:
                    raise ValidationError(
                        _(
                            "A reservation may use more than one budget code only "
                            "if every code is marked ถัวจ่ายได้ (cross-chargeable). "
                            "These are not: %s"
                        )
                        % ", ".join(blocked.mapped("display_name"))
                    )

    # --- Immutability ---

    def write(self, vals):
        if PROTECTED_FIELDS & set(vals):
            posted = self.filtered(lambda l: l.state == "posted")
            if posted:
                raise UserError(
                    _("Cannot edit posted ledger lines. Cancel and create a new entry instead.")
                )
        return super().write(vals)

    def unlink(self):
        posted = self.filtered(lambda l: l.state == "posted")
        if posted:
            raise UserError(
                _("Cannot delete posted ledger lines. Cancel them instead.")
            )
        return super().unlink()

    # --- Actions ---

    def action_cancel(self):
        """Cancel the events and their own ledger moves; a top-up living in a
        transfer's move is reversed with a new move instead of touching the
        transfer (ADR-0016, Q6)."""
        to_cancel = self.filtered(lambda l: l.state != "cancel")
        to_cancel.budget_move_id.filtered(lambda m: m.state != "cancel").sudo().with_context(
            budget_ledger_posting=True
        ).button_cancel()
        foreign = to_cancel.filtered(
            lambda l: l.budget_move_line_id and not l.budget_move_id
        )
        # Reverse the foreign lines before the state change re-checks the
        # limits, so the check never sees a half-cancelled ledger.
        for line in foreign:
            line._post_ledger_reversal()
        to_cancel.write({"state": "cancel"})
        to_cancel._check_commitment_limits()
        # Re-derive header state band (e.g. partial -> reserved once every
        # obligate/consume line is cancelled).
        to_cancel.mapped("commitment_id")._sync_state()

    def action_post(self):
        for line in self:
            if line.state != "posted":
                line.state = "posted"

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------
    def _post_budget_moves(self):
        """Post each new event of an active reservation to the ledger.

        A draft reservation's events wait for ``action_reserve``; a transfer
        top-up arrives with its ledger line already in the transfer's move.
        """
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
                     document never obligated (so an over-consume of an
                     obligation is still blocked by the limits, as before, and
                     a document never liquidates another document's obligation
                     on a shared reservation)
        A negative amount (a return, a de-obligation, a refund) mirrors it; a
        refund goes back to the bucket the source's consumes liquidated.

        On a ถัวจ่าย reservation every event but a reserve is split over its
        budget codes in order (ADR-0017): obligate/consume and a refund take
        the primary code first, a return/de-obligation gives back the last
        first.
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
            # Only a source that never obligated (net of de-obligations) draws
            # on the reserve; once it has, it consumes its obligation — so a
            # consume beyond what it obligated still overdraws the obligate
            # bucket and is blocked, rather than quietly eating the reserve.
            obligated = sum(
                self._ledger_code_held("obligate", event_type="obligate").values()
            )
            from_reserve = currency.compare_amounts(obligated, 0.0) <= 0
            bucket = "reserve" if from_reserve else "obligate"
            held = self._ledger_code_held(bucket, own=not from_reserve)
            if (
                not from_reserve
                and self.res_model
                and currency.compare_amounts(amount, sum(held.values())) > 0
            ):
                # On a shared reservation the reservation-wide limits would let
                # this document eat another one's open obligation.
                raise ValidationError(
                    _(
                        "Consumption %(amount).2f exceeds what %(source)s still "
                        "has obligated (%(held).2f)."
                    )
                    % {
                        "amount": amount,
                        "source": self.res_name or self.res_model,
                        "held": sum(held.values()),
                    }
                )
            parts = self._ledger_split(amount, held)
        else:
            liquidated = -sum(
                self._ledger_code_held("reserve", liquidated_by="consume").values()
            )
            from_reserve = currency.compare_amounts(liquidated, -amount) >= 0
            bucket = "reserve" if from_reserve else "obligate"
            # A refund goes back to the primary code first (ADR-0017).
            parts = self._ledger_split(
                -amount, self._ledger_code_held("consume"), sign=-1
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

    def _ledger_code_held(
        self, bucket, own=True, liquidated_by=None, event_type=None
    ):
        """{budget code: amount held in ``bucket``} (−Σ posted balance) on this
        event's reservation — of this event's source document only when
        ``own`` and the event has one. ``liquidated_by`` keeps only the
        liquidation lines of that event type; ``event_type`` keeps only the
        lines posted by events of that type."""
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
        if event_type:
            domain.append(("commitment_line_id.move_type", "=", event_type))
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

    # --- CRUD ---

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        # B1: forward obligate/consume are only allowed on an active commitment.
        # Exempt are reserve lines (created with the header while still draft) and
        # reversal lines (negative amount — refunds / de-obligations, which must
        # stay postable even after a commitment is fully consumed/"done");
        # _sync_state re-derives the state band once a reversal lands.
        blocked = lines.filtered(
            lambda l: l.state == "posted"
            and l.move_type in ("obligate", "consume")
            and l.amount > 0
            and l.commitment_id.state not in ("reserved", "partial")
        )
        if blocked:
            raise UserError(
                _(
                    "Can only obligate or consume a commitment that is "
                    "reserved or in progress."
                )
            )

        lines._post_budget_moves()

        # Re-derive the header state band (reserved/partial/done) from the
        # updated line totals.
        lines.mapped("commitment_id")._sync_state()

        return lines

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
        # The header is not stamped as the event: the reversal undoes an
        # event, it is not one.
        vals = dict(
            self._prepare_ledger_move_vals(),
            commitment_line_id=False,
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
                "budget ledger back-fill: consume move %s (%.2f) differs from "
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
            }
        )
        self.budget_move_line_id = primary
        return move
