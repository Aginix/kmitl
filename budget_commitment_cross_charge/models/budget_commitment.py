from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
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
                    + record._split_candidate_domain()
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
            extra = self._split_candidate_domain()
            if extra:
                refused = others.account_id - others.account_id.filtered_domain(extra)
                if refused:
                    problems.append(
                        _("รหัสต่อไปนี้ใช้ถัวจ่ายในเอกสารนี้ไม่ได้: %s")
                        % ", ".join(refused.mapped("display_name"))
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
        """แก้ไขใบจอง: re-cut a reserved, unused reservation to its split —
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
                _("ใบจอง %s มีการผูกพัน เบิกจ่าย หรือส่งคืนแล้ว แก้ไขใบจองไม่ได้") % self.name
            )
        self._check_split()
        current = {
            (line.account_id, line.amount) for line in self._pending_reserve_lines()
        }
        wanted = {(s.account_id, s.amount) for s in self.split_ids if s.amount > 0}
        # A dimension change re-cuts too: the events carry the coordinate.
        same_coordinate = all(
            (line.analytic_distribution or {}) == (self.analytic_distribution or {})
            for line in self._pending_reserve_lines()
        )
        if current == wanted and same_coordinate:
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

    # Header fields whose change re-derives row ★ and re-cuts a reserved slip.
    _SPLIT_HEADER_FIELDS = {
        "amount",
        "account_id",
        "analytic_distribution",
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    }

    def write(self, vals):
        self._check_owner_write(vals)
        nested = self.env.context.get("budget_split_batch")
        res = super(BudgetCommitment, self.with_context(budget_split_batch=True)).write(
            vals
        )
        # Once per save: the dimension inverses write again from inside.
        if not nested and ({"split_ids"} | self._SPLIT_HEADER_FIELDS) & set(vals):
            self.filtered("split_ids")._on_split_changed()
        if (
            not nested
            and not self.env.context.get("budget_slip_from_request")
            and (self._SPLIT_HEADER_FIELDS - {"amount"}) & set(vals)
        ):
            self._check_owner_budget_fields()
            self._sync_owner_from_slip()
        return res

    # --- Owner documents (พ.1, คำขออนุมัติ) ---

    def _get_split_owner(self):
        """The document whose dialog owns this slip's split, or False. Owner
        bridges override it and widen ``split_editable`` to their windows; the
        owner model names its budget committer group in
        ``_cross_charge_group``."""
        self.ensure_one()
        return False

    def _split_candidate_domain(self):
        """Extra domain a ถัว code must match for this slip's owner."""
        return []

    # What an owner's dialog may change: the split, the primary code and the
    # dimensions. The วงเงิน stays the owner's total.
    _SPLIT_DIALOG_FIELDS = _SPLIT_HEADER_FIELDS - {"amount"} | {"split_ids"}

    def _check_owner_write(self, vals):
        """An owner's budget committer holds write on the slip for the dialog
        fields only, and only inside the owner's windows — no Budget User
        rights (ADR-0020)."""
        if (
            not self.env.su
            and not self.env.user.has_group("budget.group_budget_user")
            and not self.env.user.has_group(
                "purchase_request_budget.group_purchase_request_budget_commit"
            )
            and not self.env.user.has_group("agx_approval.group_approval_budget_commit")
        ):
            if set(vals) - self._SPLIT_DIALOG_FIELDS:
                raise AccessError(
                    _("แก้ไขได้เฉพาะรหัสงบ มิติ และรายการจองงบประมาณ (ถัวจ่าย) ของใบจอง")
                )
            for record in self:
                if not record._is_owner_committer():
                    raise UserError(
                        _("ใบจอง %s แก้ไขรายการจองงบประมาณ (ถัวจ่าย) ในขั้นนี้ไม่ได้")
                        % record.display_name
                    )
        # Clearing the code or a dimension is refused up front, before the
        # re-cut reports it as a budget shortfall.
        cleared = [f for f in self._OWNER_REQUIRED_FIELDS if f in vals and not vals[f]]
        if cleared and any(record._get_split_owner() for record in self):
            labels = dict(self._owner_required_labels())
            raise UserError(
                _("กรุณาระบุข้อมูลงบประมาณให้ครบ: %s")
                % ", ".join(labels[f] for f in cleared)
            )

    def _is_owner_committer(self):
        """This slip's owner is in its window and the user is its committer."""
        self.ensure_one()
        owner = self._get_split_owner()
        return bool(
            owner
            and self.split_editable
            and self.env.user.has_group(owner._cross_charge_group)
        )

    _OWNER_REQUIRED_FIELDS = (
        "account_id",
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )

    def _owner_required_labels(self):
        return [
            ("account_id", _("รหัสงบประมาณ")),
            ("department_analytic_id", _("ส่วนงาน")),
            ("source_analytic_id", _("แหล่งเงิน")),
            ("fund_analytic_id", _("กองทุน")),
            ("activity_analytic_id", _("กิจกรรม")),
        ]

    def _check_owner_budget_fields(self):
        """An owner's slip needs its code and all four dimensions, as Reserve
        on the owner demands."""
        for record in self:
            if not record._get_split_owner():
                continue
            missing = [
                label
                for fname, label in self._owner_required_labels()
                if not record[fname]
            ]
            if missing:
                raise UserError(_("กรุณาระบุข้อมูลงบประมาณให้ครบ: %s") % ", ".join(missing))

    def _sync_owner_from_slip(self):
        """Copy the slip's primary code and dimensions back to its owner (and
        the owner's lines), so the owner and its letter follow the slip."""
        for record in self.sudo():
            owner = record._get_split_owner()
            if not owner or not record._is_split_capable():
                continue
            vals = {}
            if owner.budget_account_id != record.account_id:
                vals["budget_account_id"] = record.account_id.id
            distribution = record.analytic_distribution or False
            if (owner.analytic_distribution or False) != distribution:
                vals["analytic_distribution"] = distribution
            if not vals:
                continue
            owner.write(vals)
            if (
                "analytic_distribution" in vals
                and owner.line_ids
                and "analytic_distribution" in owner.line_ids._fields
            ):
                owner.line_ids.write({"analytic_distribution": distribution})
            owner.message_post(
                body=_("เปลี่ยนรหัสงบประมาณ/มิติตามใบจอง %s") % record.display_name,
                subtype_xmlid="mail.mt_note",
            )

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
        # sudo: the card shows on documents (คำขออนุมัติ, DR…) whose users can
        # read the reservation but hold no access to its split rows.
        for record, info in zip(self.sudo(), infos):
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
