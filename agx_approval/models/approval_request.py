from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class ApprovalRequest(models.Model):

    _name = "approval.request"
    _description = "Approval Request"
    _inherit = [
        "analytic.mixin",
        "budget.commitment.mixin",
        "mail.thread",
        "mail.activity.mixin",
    ]
    _order = "name desc"

    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string='Document Attachments',
        tracking=True,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
    )

    # -- editability gates -------------------------------------------------
    # The plan (expense lines, participants, header details) is editable while
    # the request is a draft. Bridges widen this: a Sarabun-returned request
    # reopens the plan for editing (except budget) — see agx_approval_sarabun.
    is_plan_editable = fields.Boolean(compute="_compute_is_plan_editable")
    # The actual expense allocation is filled after the mission, in `actual`.
    is_actual_editable = fields.Boolean(compute="_compute_is_actual_editable")
    # Return-correction mode — only clerical fields (recipient bank,
    # description, evidence) are editable. Always False in base; a bridge sets
    # it (e.g. agx_approval_disbursement, when a disbursement is returned).
    is_correction = fields.Boolean(compute="_compute_is_correction")

    is_budget_editable = fields.Boolean(compute="_compute_is_budget_editable")

    hide_reserve_budget_button = fields.Boolean(
        compute="_compute_hide_reserve_budget_button"
    )

    currency_id = fields.Many2one(
        string="Currency",
        comodel_name="res.currency",
        related="company_id.currency_id",
        readonly=True,
    )

    total_amount = fields.Monetary(
        compute="_compute_total_amount",
        string="Total Estimated Cost",
        currency_field="currency_id",
        store=True,
    )

    total_actual_amount = fields.Monetary(
        compute="_compute_total_actual_amount",
        string="รวมยอดเบิกจริง",
        currency_field="currency_id",
        store=True,
    )

    category_id = fields.Many2one(
        string="Category",
        comodel_name="approval.category",
        required=True,
        tracking=True,
    )

    name = fields.Char(
        string="Name",
        default="/",
        required=True,
        copy=False,
        tracking=True,
    )

    date = fields.Date(
        string="Request Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )

    owner_id = fields.Many2one(
        string="Request Owner",
        comodel_name="hr.employee",
        default=lambda self: self.env.user.employee_id,
        required=True,
        tracking=True,
    )

    user_id = fields.Many2one(
        string="Responsible Person",
        comodel_name="res.users",
        default=lambda self: self.env.uid,
        required=True,
        tracking=True,
    )

    description = fields.Text(
        string="Description",
        tracking=True,
    )

    date_start = fields.Date(
        string="Date Start",
        tracking=True,
    )

    date_end = fields.Date(
        string="Date End",
        tracking=True,
    )

    city = fields.Char(
        string="City",
        tracking=True,
    )

    country_id = fields.Many2one(
        string="Country",
        comodel_name="res.country",
        tracking=True,
    )

    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    line_ids = fields.One2many(
        "approval.request.line",
        "request_id",
        string="Expense Lines",
        copy=True,
    )

    participant_ids = fields.One2many(
        "approval.request.participant",
        "request_id",
        string="รายชื่อ",
        copy=True,
    )

    allocation_ids = fields.One2many(
        "approval.request.allocation",
        "request_id",
        string="ค่าใช้จ่ายจริง",
        copy=False,
    )

    has_period = fields.Boolean(
        related='category_id.has_period'
    )

    has_city = fields.Boolean(
        related='category_id.has_city'
    )

    has_country_id = fields.Boolean(
        related='category_id.has_country_id'
    )

    state = fields.Selection([
        ("draft", "Draft"),
        ("to_verify", "รอตรวจสอบ / จองงบประมาณ"),
        ("to_send", "รอส่งขออนุมัติ"),
        ("sent", "ส่งขออนุมัติแล้ว"),
        ("approved", "คำขอได้รับอนุมัติแล้ว"),
        ("actual", "บันทึกค่าใช้จ่ายจริง"),
        ("billed", "เบิกแล้ว"),
        ("returned", "ตีกลับ"),
        ("rejected", "ปฏิเสธ"),
    ],
        default="draft",
        copy=False,
        tracking=True,
        string="สถานะ"
    )

    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        readonly=True,
        copy=False,
        help="Related budget commitment for this approval request",
    )

    budget_commitment_amount = fields.Monetary(
        related="budget_commitment_id.amount",
        string="Reserved Amount",
        currency_field="currency_id",
        readonly=True,
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=lambda self: self._domain_budget_account_id(),
        tracking=True,
    )

    def _domain_budget_account_id(self):
        return [("purchase_ok", "=", True), ("product_id", "!=", False)]

    def _reservation_account_domain(self):
        """Budget codes selectable in the reservation picker for this request.

        Mirror the budget_account_id field domain (purchasable, product-backed
        codes) on top of the mixin's budgetable/expense baseline, so the picker
        cannot offer — and apply_reservation_selection cannot write — a code the
        request rejects.
        """
        return super()._reservation_account_domain() + self._domain_budget_account_id()

    def apply_reservation_selection(self, selections, dims=None):
        """Picker write-back: set the budget code + dimensions, then push the
        distribution onto the request lines (the analytic_distribution onchange
        does not fire on an ORM write)."""
        res = super().apply_reservation_selection(selections, dims=dims)
        if (
            self.analytic_distribution
            and self.line_ids
            and "analytic_distribution" in self.line_ids._fields
        ):
            self.line_ids.update({"analytic_distribution": self.analytic_distribution})
        return res

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
        tracking=True,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        tracking=True,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=False,
        tracking=True,
        search="_search_source_analytic_id",
    )

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        store=True,
        compute="_compute_date_range_fy",
        search="_search_date_range_fy",
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
    }

    @api.onchange("category_id")
    def _onchange_category_id(self):
        self.line_ids = False
        self.participant_ids = False
        self.description = self.category_id.default_description
        if self.category_id:
            self.budget_account_id = self.category_id.budget_account_id
            distribution = {}
            for field_name in (
                "activity_analytic_id",
                "department_analytic_id",
                "fund_analytic_id",
                "source_analytic_id",
            ):
                analytic = self.category_id[field_name]
                if analytic:
                    distribution[str(analytic.id)] = 100
            self.analytic_distribution = distribution or False

    @api.model
    def _search_source_analytic_id(self, operator, value):
        account_ids = []
        if type(value) == int:
            account_ids.append(value)
        else:
            account_ids = (
                self.env["account.analytic.account"]
                .search(
                    [
                        ("root_plan_id.code", "=", "sources"),
                        "|",
                        ("name", "ilike", value),
                        ("complete_name", "ilike", value),
                    ]
                )
                .mapped("id")
            )

        query = f"""
            SELECT id
            FROM {self._table}
            WHERE analytic_distribution ?| array[%s]
        """
        return [
            (
                "id",
                "inselect",
                (query, [[str(account_id) for account_id in account_ids]]),
            )
        ]

    @api.depends("date", "company_id")
    def _compute_date_range_fy(self):
        for rec in self:
            date = fields.Date.to_date(rec.date)
            company = rec.company_id
            rec.account_fiscal_year_id = (
                company and company.find_daterange_fy(date) or False
            )

    @api.model
    def _search_date_range_fy(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]

        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)

        domain = [("id", "=", -1)]
        for date_range in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("date", ">=", date_range.date_from),
                        ("date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """When change analytic_distribution set analytic distribution on all order lines"""
        if self.analytic_distribution and self.line_ids and "analytic_distribution" in self.line_ids._fields:
            self.line_ids.update({"analytic_distribution": self.analytic_distribution})

    def _inverse_activity_analytic(self):
        """Update distribution when activity changes"""
        for line in self:
            line._update_analytic_distribution("activities")

    def _inverse_department_analytic(self):
        """Update distribution when department changes"""
        for line in self:
            line._update_analytic_distribution("departments")

    def _inverse_fund_analytic(self):
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("funds")

    def _inverse_source_analytic(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("sources")

    # -- transitions -------------------------------------------------------
    def action_to_verify(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft requests can be verified."))
            if not record.line_ids:
                raise UserError(_("กรุณาเพิ่มรายการค่าใช้จ่าย (แผน) อย่างน้อย 1 รายการ"))
            zero_lines = record.line_ids.filtered(lambda l: l.total_amount <= 0)
            if zero_lines:
                names = ", ".join(zero_lines.mapped("product_id.name"))
                raise UserError(
                    _("รายการค่าใช้จ่ายต่อไปนี้ต้องระบุจำนวนเงินมากกว่า 0: %s") % names
                )
            if not record.participant_ids:
                raise UserError(_("กรุณาเพิ่มรายชื่ออย่างน้อย 1 รายชื่อ"))
            record.state = "to_verify"
        return True

    def action_submit(self):
        for record in self:
            if record.state != "to_verify":
                raise UserError(_("Only To Verify requests can be submitted."))
            record.state = "to_send"
        return True

    def action_approve(self):
        """Internal approval fallback for installations without the Sarabun
        bridge. When agx_approval_sarabun is installed the request is approved
        by the Sarabun document outcome instead (see _on_sarabun_completed)."""
        for record in self:
            if record.state not in ("to_send", "sent"):
                raise UserError(
                    _("Only submitted requests can be approved.")
                )
            record.state = "approved"
        return True

    def action_record_actual(self):
        """Approved → actual: the requester comes back from the mission and
        records the actual expense allocation before billing."""
        for record in self:
            if record.state != "approved":
                raise UserError(
                    _("Only approved requests can record actual expenses.")
                )
            record.state = "actual"
        return True

    def action_bill(self):
        for record in self:
            if record.state != "actual":
                raise UserError(
                    _("Only requests with recorded actuals can be billed.")
                )
            record.state = "billed"
        return True

    def action_cancel(self):
        for record in self:
            if record.state == "rejected":
                raise UserError(_("Request is already rejected."))
            record.state = "rejected"
            record._release_budget_commitment(_("cancelled"))
        return True

    def action_draft(self):
        for record in self:
            record.state = "draft"
            record._release_budget_commitment(_("reset to draft"))
        return True

    def action_open_pull_back_wizard(self):
        """ดึงกลับ (pre-routing): open the confirm wizard that returns a
        not-yet-sent request to draft."""
        self.ensure_one()
        if self.state not in ("to_verify", "to_send"):
            raise UserError(
                _("ดึงกลับได้เฉพาะสถานะ 'รอตรวจสอบ' หรือ 'รอส่งขออนุมัติ'")
            )
        wizard = self.env["approval.request.pull.back.confirm"].create({
            "request_id": self.id,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("ดึงกลับคำขอ"),
            "res_model": "approval.request.pull.back.confirm",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    def _release_budget_commitment(self, reason):
        """Cancel the reserved commitment (if any), logging the reason."""
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.message_post(
                        body=_("Budget commitment %(name)s has been cancelled (%(reason)s)")
                        % {
                            "name": record.budget_commitment_id.name,
                            "reason": reason,
                        }
                    )
                except UserError as e:
                    record.message_post(
                        body=_("Warning: Could not cancel budget commitment: %s")
                        % str(e)
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "approval.request"
                ) or "/"

        records = super().create(vals_list)
        for rec in records:
            if rec.budget_commitment_id:
                rec._log_budget_commitment_linked()
        return records

    def _log_budget_commitment_linked(self):
        link = f"/web#id={self.id}&model={self._name}&view_type=form"
        self.budget_commitment_id.message_post(
            body=_(
                'The account move request <a href="%(link)s" target="_blank">\'%(name)s\'</a> has been linked to this record.'
            )
            % {"name": self.name, "link": link},
            subtype_xmlid="mail.mt_comment",
        )

    def _log_budget_commitment_unlinked(self):
        link = f"/web#id={self.id}&model={self._name}&view_type=form"
        self.budget_commitment_id.message_post(
            body=_("The account move request '%(name)s' has been unlinked.")
            % {"name": self.name},
            subtype_xmlid="mail.mt_comment",
        )

    def action_open_budget_commitment(self):
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError(_("ยังไม่มี Budget Commitment สำหรับเอกสารนี้"))

        return {
            "type": "ir.actions.act_window",
            "name": "Budget Commitment",
            "res_model": "budget.commitment",
            "view_mode": "form",
            "res_id": self.budget_commitment_id.id,
            "target": "current",
        }

    def action_reserve_budget(self):
        """Reserve budget by creating commitment"""
        self.ensure_one()

        amount = sum(self.line_ids.mapped("total_amount"))

        # ปีงบยึดตามเอกสาร: check/reserve against this request's own fiscal year
        # (account_fiscal_year_id, derived from its date), not today() — otherwise a
        # request whose FY differs from today is checked against the wrong year.
        check_result = self._check_budget_availability(
            amount=amount,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
            account_fiscal_year_id=self.account_fiscal_year_id.id,
        )

        if not check_result["is_sufficient"]:
            raise UserError(
                _("Cannot reserve budget due to insufficient funds: %s")
                % check_result["message"]
            )

        try:
            commitment = self._create_budget_commitment(
                amount=amount,
                activity_analytic_id=self.activity_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
                ref=self.name,
                description=f"Approval Request: {self.name}",
                auto_reserve=True,
                account_fiscal_year_id=self.account_fiscal_year_id.id,
            )
            self.message_post(
                body=_("Budget reserved: %s for amount %s") % (commitment.name, amount)
            )
            self.action_submit()
            return {
                "type": "ir.actions.act_window",
                "res_model": "approval.request",
                "view_mode": "form",
                "res_id": self.id,
                "target": "current",
                "context": self.env.context,
            }

        except UserError as e:
            raise UserError(_("Cannot reserve budget: %s") % str(e))

    @api.depends("state", "budget_commitment_id", "budget_commitment_id.state")
    def _compute_is_budget_editable(self):
        can_edit = self.env.user.has_group("budget.group_budget_commitment")
        for rec in self:
            if rec.state == "to_verify" and (
                not rec.budget_commitment_id
                or rec.budget_commitment_id.state == "cancel"
            ):
                rec.is_budget_editable = can_edit
            else:
                rec.is_budget_editable = rec.state == "draft"

    @api.depends("state", "budget_commitment_id")
    def _compute_hide_reserve_budget_button(self):
        for rec in self:
            if rec.state == "to_verify" and (
                not rec.budget_commitment_id
                or rec.budget_commitment_id.state == "cancel"
            ):
                rec.hide_reserve_budget_button = False
            else:
                rec.hide_reserve_budget_button = True

    @api.depends("state")
    def _compute_is_plan_editable(self):
        """The plan (expense lines, participants, header) is editable only in
        draft by default. agx_approval_sarabun widens this to a Sarabun-returned
        request (edit everything except budget)."""
        for rec in self:
            rec.is_plan_editable = rec.state == "draft"

    @api.depends("state")
    def _compute_is_actual_editable(self):
        for rec in self:
            rec.is_actual_editable = rec.state == "actual"

    def _compute_is_correction(self):
        # Base has no return-correction mode; bridges override this.
        for rec in self:
            rec.is_correction = False

    @api.depends("line_ids.total_amount")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped("total_amount"))

    @api.depends("allocation_ids.amount")
    def _compute_total_actual_amount(self):
        for rec in self:
            rec.total_actual_amount = sum(rec.allocation_ids.mapped("amount"))

    def _voucher_groups(self):
        """งบหน้าใบสำคัญคู่จ่าย data: the disbursed actual allocation — จ่ายตรง /
        สำรองจ่าย only; เงินยืม is excluded (it clears against the สัญญายืม, not a
        disbursement) — grouped per recipient, with the per-recipient subtotal,
        withholding-tax total and voucher (line) count."""
        self.ensure_one()
        groups = []
        allocations = self.allocation_ids.filtered(
            lambda a: a.payment_type != "advance"
        )
        for recipient in allocations.mapped("partner_id"):
            allocs = allocations.filtered(
                lambda a: a.partner_id == recipient
            )
            wht_total = sum(a._wht_amount() for a in allocs)
            groups.append({
                "recipient": recipient,
                "allocs": allocs,
                "subtotal": sum(allocs.mapped("amount")),
                "wht_total": wht_total,
                "voucher_count": len(allocs),
                "has_wht": bool(wht_total),
            })
        return groups

    @api.constrains("allocation_ids", "state")
    def _check_allocation_within_budget(self):
        """The recorded actuals may not exceed the approved plan / reserved
        budget."""
        for rec in self:
            if not rec.allocation_ids:
                continue
            cap = rec.budget_commitment_amount or rec.total_amount
            if cap and rec.currency_id.compare_amounts(
                rec.total_actual_amount, cap
            ) > 0:
                raise ValidationError(
                    _(
                        "ยอดค่าใช้จ่ายจริง (%(actual)s) เกินงบที่อนุมัติ/จองไว้ (%(cap)s)"
                    )
                    % {"actual": rec.total_actual_amount, "cap": cap}
                )
