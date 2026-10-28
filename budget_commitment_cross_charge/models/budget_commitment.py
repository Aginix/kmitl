from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    # The declared per-code plan of the reservation (ถัวจ่าย, ADR-0020).
    split_ids = fields.One2many(
        comodel_name="budget.commitment.split",
        inverse_name="commitment_id",
        string="รายการจองงบประมาณ",
        copy=True,
    )
    split_editable = fields.Boolean(
        compute="_compute_split_editable",
        help="Whether the รายการจองงบประมาณ may be edited now (ADR-0020).",
    )
    split_account_ids = fields.Many2many(
        comodel_name="budget.account",
        compute="_compute_split_account_ids",
        help="Codes a new ถัว row may name: flagged ถัวจ่ายได้, funded at this "
        "reservation's dimensions and not on a row yet.",
    )
    split_warning = fields.Text(compute="_compute_split_warning")

    @api.depends("state", "kmitl_project_analytic_id", "procurement_plan_analytic_id")
    def _compute_split_editable(self):
        """Standalone slips: while draft. A project or plan slip (it carries a
        Pool Tag) stays single-code. Owners widen this (the พ.1, ADR-0020)."""
        for record in self:
            record.split_editable = (
                record.state == "draft" and record._is_split_capable()
            )

    def _is_split_capable(self):
        self.ensure_one()
        return not (self.kmitl_project_analytic_id or self.procurement_plan_analytic_id)

    @api.depends(
        "account_id",
        "analytic_distribution",
        "account_fiscal_year_id",
        "split_editable",
        "split_ids.account_id",
    )
    def _compute_split_account_ids(self):
        Account = self.env["budget.account"].sudo()
        controller = self.env["budget.controller"].sudo()
        for record in self:
            eligible = Account
            if (
                record.split_editable
                and record.account_id.cross_chargeable
                and record.account_fiscal_year_id
            ):
                distribution = record._availability_distribution()
                candidates = Account.search(
                    [
                        ("cross_chargeable", "=", True),
                        ("budgetable", "=", True),
                        ("budget_type", "=", "expense"),
                        ("id", "!=", record.account_id.id),
                    ]
                )
                for account in candidates:
                    available = controller.get_available_detail(
                        account,
                        distribution,
                        record.account_fiscal_year_id.id,
                        record.company_id.id,
                    )["available"]
                    if available > 0:
                        eligible |= account
            # Not the codes already on a row: one row per code (unique), and
            # the dropdown of a new row must not offer a duplicate.
            record.split_account_ids = eligible - record.split_ids.account_id

    @api.depends(
        "amount",
        "account_id",
        "split_ids.amount",
        "split_ids.account_id",
        "split_ids.available",
    )
    def _compute_split_warning(self):
        for record in self:
            record.split_warning = "\n".join(record._split_problems()) or False

    def _split_problems(self):
        """Why the รายการจองงบประมาณ cannot be reserved as it stands."""
        self.ensure_one()
        problems = []
        splits = self.split_ids
        if not splits:
            return problems
        currency = self.currency_id or self.env.company.currency_id
        primary = splits.filtered("is_primary")
        others = splits - primary
        # Row ★ may end at 0 (the whole วงเงิน on ถัว codes), never below.
        if primary and currency.compare_amounts(primary.amount, 0.0) < 0:
            problems.append(
                _("ยอดถัวจ่ายรวม %(others)s เกินวงเงิน %(cap)s")
                % {
                    "others": formatLang(
                        self.env, sum(others.mapped("amount")), currency_obj=currency
                    ),
                    "cap": formatLang(self.env, self.amount, currency_obj=currency),
                }
            )
        for split in others.filtered(
            lambda s: currency.compare_amounts(s.amount, 0.0) <= 0
        ):
            problems.append(
                _("รหัส %s: ระบุยอดถัวจ่ายมากกว่า 0 หรือลบแถวนี้")
                % split.account_id.display_name
            )
        if others:
            blocked = splits.account_id.filtered(lambda a: not a.cross_chargeable)
            if blocked:
                problems.append(
                    _("รหัสต่อไปนี้ยังไม่ได้ตั้งค่า ถัวจ่ายได้: %s")
                    % ", ".join(blocked.mapped("display_name"))
                )
        for split in splits.filtered(lambda s: s.account_id and not s.is_sufficient):
            problems.append(
                _(
                    "รหัส %(code)s: งบไม่พอ ขาด %(short)s (จอง %(amount)s งบที่จองได้ %(available)s)"
                )
                % {
                    "code": split.account_id.display_name,
                    "short": formatLang(
                        self.env, split.amount - split.available, currency_obj=currency
                    ),
                    "amount": formatLang(self.env, split.amount, currency_obj=currency),
                    "available": formatLang(
                        self.env, split.available, currency_obj=currency
                    ),
                }
            )
        return problems

    @api.onchange("amount", "account_id", "split_ids")
    def _onchange_split_primary(self):
        """Keep row ★ on the header code and at the remainder as the user types."""
        if self.split_ids:
            self._sync_split_primary()

    def _sync_split_primary(self):
        """Row ★ = the header code, amount = วงเงิน − Σ ถัว rows (ADR-0020).
        Creates the row when missing; a ถัว row naming the header code is
        merged into it."""
        for record in self.with_context(budget_split_sync=True):
            if not record.account_id:
                continue
            Split = record.env["budget.commitment.split"]
            primary = record.split_ids.filtered("is_primary")[:1]
            duplicate = record.split_ids.filtered(
                lambda s, r=record: not s.is_primary and s.account_id == r.account_id
            )
            if duplicate:
                if isinstance(record.id, models.NewId):
                    record.split_ids -= duplicate
                else:
                    duplicate.unlink()
            others = record.split_ids.filtered(lambda s: not s.is_primary)
            amount = record.amount - sum(others.mapped("amount"))
            if not primary:
                vals = {
                    "is_primary": True,
                    "sequence": 0,
                    "account_id": record.account_id.id,
                    "amount": amount,
                }
                if isinstance(record.id, models.NewId):
                    record.split_ids |= Split.new(vals)
                else:
                    Split.create(dict(vals, commitment_id=record.id))
                continue
            if primary.account_id != record.account_id:
                primary.account_id = record.account_id
            if (record.currency_id or self.env.company.currency_id).compare_amounts(
                primary.amount, amount
            ):
                primary.amount = amount

    def _on_split_changed(self):
        """After a save touched the split: re-derive row ★, and re-cut a
        reserved reservation (ADR-0020)."""
        self._sync_split_primary()
        for record in self:
            if record.state == "reserved" and record.split_ids:
                record.sudo()._recut_reserve_split()

    def _check_split(self):
        problems = self._split_problems()
        if problems:
            raise UserError("\n".join(problems))

    def _create_reserve_lines_from_split(self):
        """One reserve event per row, row ★ first, so ADR-0018's liquidation
        order is the split's order."""
        self.ensure_one()
        vals_list = []
        for split in self.split_ids.filtered(lambda s: s.amount > 0):
            vals = self._prepare_budget_event_vals(
                "reserve", split.amount, name=_("Reservation")
            )
            vals["account_id"] = split.account_id.id
            vals_list.append(vals)
        return self.env["budget.commitment.line"].create(vals_list)

    def _recut_reserve_split(self):
        """ปรับถัวจ่าย: re-cut a reserved, unused reservation to its split —
        cancel the reserve events, re-check every pool with this reservation
        given back, then post the new events."""
        self.ensure_one()
        used = self.line_ids.filtered(
            lambda line: (
                line.state == "posted"
                and (line.move_type != "reserve" or line.is_return)
            )
        )
        if used:
            raise UserError(
                _("ใบจอง %s มีการผูกพัน เบิกจ่าย หรือส่งคืนแล้ว ปรับถัวจ่ายไม่ได้") % self.name
            )
        self._check_split()
        current = {
            (line.account_id, line.amount) for line in self._pending_reserve_lines()
        }
        wanted = {(s.account_id, s.amount) for s in self.split_ids if s.amount > 0}
        if current == wanted:
            return
        self._pending_reserve_lines().action_cancel()
        amounts = {}
        for split in self.split_ids.filtered(lambda s: s.amount > 0):
            amounts[split.account_id] = split.amount
        self._check_reserve_availability(amounts)
        self._create_reserve_lines_from_split()
        self.message_post(
            body=_("ปรับรายการจองงบประมาณ (ถัวจ่าย): %s")
            % ", ".join(
                "%s %s"
                % (
                    split.account_id.display_name,
                    formatLang(self.env, split.amount, currency_obj=self.currency_id),
                )
                for split in self.split_ids
            )
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(
            BudgetCommitment, self.with_context(budget_split_batch=True)
        ).create(vals_list)
        records = records.with_env(self.env)
        records.filtered("split_ids")._sync_split_primary()
        return records

    def write(self, vals):
        res = super(BudgetCommitment, self.with_context(budget_split_batch=True)).write(
            vals
        )
        if {"split_ids", "amount", "account_id"} & set(vals):
            self.filtered("split_ids")._on_split_changed()
        return res

    # --- Hooks into the core reservation ---

    def _create_reserve_line_from_header(self):
        """จองงบ on a slip with a split: one reserve event per row instead of
        the single header line."""
        if not self.split_ids:
            return super()._create_reserve_line_from_header()
        self._sync_split_primary()
        self._check_split()
        return self._create_reserve_lines_from_split()

    def get_reservation_info(self):
        """The info card lists a ถัวจ่าย reservation's codes as a table."""
        infos = super().get_reservation_info()
        for record, info in zip(self, infos):
            if len(record.split_ids) > 1:
                info["lines_label"] = _("รายการจองงบประมาณ (ถัวจ่าย)")
                info["lines"] = [
                    {
                        "primary": split.is_primary,
                        "code": split.account_id.code or "",
                        "name": split.account_id.name,
                        "amount": formatLang(
                            self.env, split.amount, currency_obj=record.currency_id
                        ),
                    }
                    for split in record.split_ids
                ]
        return infos
