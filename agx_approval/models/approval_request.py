from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError


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
    is_budget_editable = fields.Boolean(compute="_compute_is_budget_editable")

    # True once the official AR/<be>/#### number has been minted. Used by the
    # view to freeze account_fiscal_year_id and to swap the title for a "New"
    # label while the number is still the placeholder.
    is_number_assigned = fields.Boolean(compute="_compute_is_number_assigned")

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

    category_id = fields.Many2one(
        string="Category",
        comodel_name="approval.category",
        required=True,
        tracking=True,
    )

    name = fields.Char(
        string="Name",
        # Untranslated placeholder, like account.move's "/": the number is minted
        # later (at submit), so this value sits in the DB and is read back by
        # users in other locales. Anything translated here would compare unequal
        # to _() evaluated in the reader's language. The friendly "New" label is
        # rendered by the form view instead.
        default="/",
        required=True,
        copy=False,
        tracking=True,
    )

    date = fields.Date(
        string="Request Date",
        copy=False,
        tracking=True,
        help="วันที่ส่งคำขอ — stamped when the request is submitted for verification "
        "(draft → รอตรวจสอบ), and re-stamped on every re-submit after a reset to "
        "draft or a ดึงกลับ. Empty until the request is first submitted: a draft "
        "has not been sent anywhere yet, so it has no submit date. NOT the "
        "creation date (that is create_date) and NOT the หนังสือ's ลงวันที่.",
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

    @api.constrains("owner_id")
    def _check_owner_is_self_for_own_group(self):
        """"Own only" users may file requests in their own name only: the
        requester (ผู้ขออนุมัติ) must be themselves. Full Users, Managers and
        superuser are unaffected."""
        if self.env.su:
            return
        user = self.env.user
        if not user.has_group(
            "agx_approval.group_approval_own"
        ) or user.has_group("agx_approval.group_approval_user"):
            return
        for rec in self:
            if rec.owner_id != user.employee_id:
                raise ValidationError(
                    _("You can only submit approval requests in your own name.")
                )

    requesting_department_id = fields.Many2one(
        "account.analytic.account",
        string="หน่วยงานผู้ขอ",
        domain=[("root_plan_id.code", "=", "departments")],
        default=lambda self: self._default_requesting_department_id(),
        tracking=True,
        index=True,
        help="หน่วยงานที่ขออนุมัติค่าใช้จ่าย — ระบุโดยผู้ขอตั้งแต่แรก แยกจากมิติ "
        "ส่วนงานของงบประมาณ (ส่วนงานที่ตัดงบ) ซึ่งเจ้าหน้าที่งบเลือกภายหลัง",
    )

    @api.model
    def _default_requesting_department_id(self):
        return self.search(
            [
                ("user_id", "=", self.env.uid),
                ("requesting_department_id", "!=", False),
            ],
            order="id desc",
            limit=1,
        ).requesting_department_id

    description = fields.Text(
        string="Description",
        tracking=True,
    )

    period_type = fields.Selection(
        [("range", "หลายวัน"), ("single", "วันเดียว")],
        string="ลักษณะระยะเวลา",
        default="range",
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

    day_portion = fields.Selection(
        [("full", "เต็มวัน"), ("half", "ครึ่งวัน")],
        string="ช่วงเวลา (วันเดียว)",
        default="full",
        tracking=True,
    )

    @api.onchange("period_type")
    def _onchange_period_type(self):
        """Clear the companion input that the chosen mode doesn't use (Odoo
        convention): a single-day request has no end date, a multi-day one has no
        day portion. Keeps the narrative unambiguous about which one applies."""
        if self.period_type == "single":
            self.date_end = False
        else:
            self.day_portion = False

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

    # A category without Expense Items (the overwhelming majority) hides the
    # line table entirely: the requester types one amount + description,
    # mirrored onto the sole `approval.request.line` behind the scenes.
    # `line_ids` stays the single source of truth (budget reserve,
    # _compute_total_amount, disbursement) — these two fields are just the
    # bare-amount UI for that case (ADR-0010).
    has_expense_items = fields.Boolean(
        related="category_id.has_expense_items",
        string="มีรายการค่าใช้จ่ายย่อย",
    )

    # Without Expense Items: mirrors the one hidden line. With them: the
    # requester's spending ceiling (เพดานค่าใช้จ่าย) the lines must add up to —
    # checked at each state transition (excep_plan_amount_mismatch), so stored.
    plan_amount = fields.Monetary(
        string="จำนวนเงิน",
        currency_field="currency_id",
        compute="_compute_plan_amount",
        inverse="_inverse_plan_single",
        store=True,
        readonly=False,
    )

    plan_description = fields.Text(
        string="รายละเอียด",
        compute="_compute_plan_single",
        inverse="_inverse_plan_single",
    )

    @api.depends("line_ids.total_amount", "category_id.has_expense_items")
    def _compute_plan_amount(self):
        # With Expense Items keep whatever ceiling the requester typed.
        for rec in self:
            if not rec.has_expense_items:
                rec.plan_amount = rec.line_ids[:1].total_amount

    @api.depends("line_ids.description", "category_id.has_expense_items")
    def _compute_plan_single(self):
        for rec in self:
            if not rec.has_expense_items and rec.line_ids:
                rec.plan_description = rec.line_ids[0].description
            else:
                rec.plan_description = False

    def _inverse_plan_single(self):
        """Mirror the bare amount/description onto the single line behind a
        category without Expense Items. Guarded on ``category_id`` and
        ``is_plan_editable`` so this never fires destructively before a
        category is chosen or once the plan is locked (see memory
        odoo16-first-onchange-runs-every-method-wipes-defaults)."""
        for rec in self:
            if rec.has_expense_items or not rec.category_id or not rec.is_plan_editable:
                continue
            # No amount yet means nothing is planned yet: drop the mirrored
            # line rather than write a 0, which approval.request.line's
            # _check_total_amount_positive rejects — otherwise a draft could
            # not be saved before the requester fills the amount in.
            if not rec.plan_amount:
                if rec.line_ids:
                    rec.line_ids = [(5, 0, 0)]
                continue
            vals = {
                "total_amount": rec.plan_amount,
                "description": rec.plan_description,
            }
            line = rec.line_ids[:1]
            if line:
                extra = rec.line_ids - line
                if extra:
                    extra.unlink()
                line.write(vals)
            else:
                rec.line_ids = [(0, 0, vals)]

    participant_ids = fields.One2many(
        "approval.request.participant",
        "request_id",
        string="รายชื่อ",
        copy=True,
    )

    internal_participant_ids = fields.One2many(
        "approval.request.participant",
        "request_id",
        string="รายชื่อบุคลากรภายใน",
        domain=[("participant_type", "=", "internal")],
        copy=False,
    )

    external_participant_ids = fields.One2many(
        "approval.request.participant",
        "request_id",
        string="รายชื่อบุคคลภายนอก",
        domain=[("participant_type", "=", "external")],
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
        ("to_verify", "รอตรวจสอบข้อมูล"),
        ("to_commit", "รอยืนยันงบประมาณ"),
        ("to_send", "รอส่งขออนุมัติ"),
        ("sent", "ส่งขออนุมัติแล้ว"),
        ("approved", "คำขอได้รับอนุมัติแล้ว"),
        ("done", "เสร็จสิ้น"),
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
        # Approval-eligible expense codes (ADR-0004, amended): the approval_ok
        # flag is the sole gate, independent of purchase_ok, so a code may be
        # reservable from both purchase requests and approval requests.
        return [
            ("budgetable", "=", True),
            ("budget_type", "=", "expense"),
            ("approval_ok", "=", True),
        ]

    budget_account_domain = fields.Binary(
        compute="_compute_budget_account_domain",
        help="Record-aware domain for รหัสงบประมาณ, now picked directly on the "
        "form (ADR-0008): the same codes the reservation picker would offer, "
        "including a category-pinned code.",
    )

    @api.depends("category_id")
    def _compute_budget_account_domain(self):
        for rec in self:
            rec.budget_account_domain = rec._reservation_account_domain()

    def _reservation_account_domain(self):
        """Budget codes selectable in the reservation picker for this request.

        Approval-eligible expense codes (approval_ok, ADR-0004) on top of the mixin's
        budgetable/expense baseline, so the picker cannot offer — and
        apply_reservation_selection cannot write — a code the request rejects.
        When the category pins a budget code, that code is the request's hard
        constraint (single choke point for picker, write-back, and draw-down).
        """
        domain = super()._reservation_account_domain() + self._domain_budget_account_id()
        if self.category_id.budget_account_id:
            # child_of, not =: the category pins a budget *branch*, so a
            # reservation may name any descendant of the funded code (ADR-0016).
            domain += [("id", "child_of", self.category_id.budget_account_id.id)]
        return domain

    def _get_commitment_title(self):
        """ชื่อรายการจอง of a commitment this request reserves = its ประเภทคำขออนุมัติ.

        The mixin's default would take the request's free-text ``description``,
        which is written for the approver, not as a label — often a whole
        paragraph. The approval category is the request's actual kind, is
        required on every request, and is what the budget side recognises the
        reservation by.
        """
        self.ensure_one()
        if self.category_id:
            return f"[{self.name}] {self.category_id.name}"
        return super()._get_commitment_title()

    budget_commitment_state = fields.Selection(
        related="budget_commitment_id.state",
        string="สถานะใบจอง",
        readonly=True,
        help=(
            "ใช้ในฟอร์มเพื่อแยก 'มีใบจองที่ยังใช้งานอยู่' ออกจาก 'ใบจองถูกยกเลิกแล้ว' "
            "— การยกเลิกใบจองไม่ล้างค่า budget_commitment_id จึงต้องดูสถานะประกอบ"
        ),
    )
    budget_selection_mode = fields.Selection(
        selection=[
            ("normal", "ใช้เงินจากแผน (จองงบใหม่)"),
        ],
        string="วิธีเลือกงบประมาณ",
        default="normal",
        copy=False,
        help=(
            "เลือกวิธีจัดหางบประมาณของคำขอนี้ — ฐานระบบมีเฉพาะการจองงบใหม่จากผังงบประมาณ "
            "โมดูลเสริมอาจเพิ่มวิธีอื่น เช่น หยิบใบจองงบประมาณของโครงการที่อนุมัติแล้วไปใช้"
        ),
    )
    reservation_commitment_id = fields.Many2one(
        "budget.commitment",
        string="ใบจองงบประมาณ",
        copy=False,
        tracking=True,
        help=(
            "เลือกใบจองงบประมาณที่มีอยู่แล้วเพื่อหยิบไปใช้ (draw down) แทนการจองใหม่ "
            "— เอกสารจะสืบทอดรหัสงบ/มิติจากใบจองแบบล็อก และไม่จองซ้ำ. "
            "ใช้เมื่อเลือกวิธี 'หยิบจากใบจองงบประมาณที่มีอยู่'."
        ),
    )

    def _reservation_commitment_mode_domain(self):
        """Which commitments the current ``budget_selection_mode`` may draw.
        Base only ships ``normal`` (reserve-new), which never draws — bridges
        add their own mode (e.g. a project's shared slip) and gate it here."""
        return [("id", "=", False)]

    def _domain_reservation_commitment_id(self):
        """Reservations this request may draw down (phase-1 dropdown), gated by
        the active ``budget_selection_mode`` via
        ``_reservation_commitment_mode_domain``. Restricted to this request's own
        ปีงบประมาณ — a slip reserved in another year would silently pull the
        request's money out of the year it declares (excep_account_fiscal_year_
        not_match_budget_commitment blocks it server-side). OU visibility (owner
        or beneficiary unit) is enforced by the record rules (ADR-0011)."""
        domain = [
            ("state", "in", ("reserved", "partial")),
            ("available_to_obligate", ">", 0),
            ("account_fiscal_year_id", "=", self.account_fiscal_year_id.id),
        ]
        domain += self._reservation_commitment_mode_domain()
        return domain

    reservation_commitment_domain = fields.Binary(
        compute="_compute_reservation_commitment_domain",
        help=(
            "Record-aware domain for the ใบจองงบประมาณ dropdown. A static field "
            "domain can neither see this request's own account_fiscal_year_id "
            "nor be extended per budget_selection_mode by a bridge, so the "
            "dropdown is driven by this computed domain instead — same pattern "
            "as purchase_request_budget."
        ),
    )

    @api.depends("account_fiscal_year_id", "budget_selection_mode")
    def _compute_reservation_commitment_domain(self):
        for rec in self:
            rec.reservation_commitment_domain = (
                rec._domain_reservation_commitment_id()
            )

    def action_open_reservation_picker(self):
        """Browse the picker in only-selectable mode: the requester may pick only
        codes this request accepts (a category-pinned code, else the
        approval-eligible baseline), so the picker collapses the ประเภทงบ chart to
        those codes and the dimension path to them instead of showing every code
        of the root category with only one clickable."""
        action = super().action_open_reservation_picker()
        action["context"] = dict(action.get("context") or {}, only_selectable=True)
        return action

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
        required=True,
        tracking=True,
        default=lambda self: self._default_account_fiscal_year_id(),
        help="ปีงบประมาณที่คำขอนี้จะใช้งบ — chosen by the user, never derived from "
        "the document date. A request drafted late in ปีงบ N to spend ปีงบ N+1 "
        "money simply picks N+1 up front and waits. The budget reservation checks "
        "and books against this year (see action_reserve_budget), so it is the "
        "request's single statement of which year's money it is spending.",
    )

    @api.model
    def _default_account_fiscal_year_id(self):
        """Today's ปีงบประมาณ — a convenience starting point, not a constraint;
        the user overrides it to file ahead for the coming year."""
        return self.env.company.find_daterange_fy(fields.Date.context_today(self))

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
        self.internal_participant_ids = False
        self.external_participant_ids = False
        self.description = self.category_id.default_description

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
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft requests can be verified."))
        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                agx_exception_action="action_to_verify"
            )._popup_exceptions()
        # วันที่ส่งคำขอ is stamped here, not at creation: a draft has not been sent
        # anywhere. Re-stamped on every pass through this transition, so a request
        # reset to draft (or ดึงกลับ) and re-submitted carries the date it was
        # actually submitted, not the first attempt's.
        vals = {"state": "to_verify", "date": fields.Date.context_today(self)}
        # Mint the official number on first submission only. Once assigned it is
        # permanent — a returned/ดึงกลับ request that comes back through here
        # keeps its number, unlike ``date`` which re-stamps.
        #
        # Mirrors procurement_plan.action_send_to_verify: the number's ปีงบ
        # comes from account_fiscal_year_id, not today — pin both %(year_be)s
        # interpolation (ir_sequence_date) and the date_range sub-sequence
        # (sequence_date) to the FY's date_to.
        if not self.is_number_assigned:
            fiscal_date = self.account_fiscal_year_id.date_to
            vals["name"] = self.env["ir.sequence"].with_context(
                ir_sequence_date=fiscal_date
            ).next_by_code(
                "approval.request",
                sequence_date=fiscal_date,
            ) or "/"
        self.write(vals)
        return True

    @api.constrains("account_fiscal_year_id")
    def _check_fiscal_year_locked_after_submission(self):
        """Once a request has an official number, its fiscal year is frozen:
        the number is minted from ``%(year_be)s`` of that FY's ``date_to``, so
        swapping the FY afterwards would silently desync AR/<year>/#### from
        the year the money is actually spent under."""
        for rec in self:
            if rec.is_number_assigned:
                raise ValidationError(
                    _(
                        "Fiscal year cannot be changed after the request has "
                        "been submitted (number %s already assigned)."
                    )
                    % rec.name
                )

    def action_confirm_verify(self):
        """ยืนยันตรวจสอบ: ผู้ตรวจสอบคำขอ hands the request to ผู้ยืนยันงบประมาณ
        (to_verify → to_commit). Budget code / dimensions need not be complete
        yet — they are checked in full at ยืนยันงบประมาณ (action_reserve_budget)."""
        self.ensure_one()
        if self.state != "to_verify":
            raise UserError(_("ยืนยันตรวจสอบได้เฉพาะสถานะ 'รอตรวจสอบข้อมูล'"))
        if not self.env.user.has_group("agx_approval.group_approval_verify"):
            raise UserError(_("คุณไม่มีสิทธิ์ยืนยันตรวจสอบคำขอ"))
        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                agx_exception_action="action_confirm_verify"
            )._popup_exceptions()
        self.state = "to_commit"
        return True

    def action_open_send_back_wizard(self):
        """ตีกลับ: open the mandatory-reason wizard that sends the request one
        step back (to_commit → to_verify, to_verify → draft)."""
        self.ensure_one()
        if self.state not in ("to_verify", "to_commit"):
            raise UserError(
                _("ตีกลับได้เฉพาะสถานะ 'รอตรวจสอบข้อมูล' หรือ 'รอยืนยันงบประมาณ'")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("ตีกลับคำขอ"),
            "res_model": "approval.request.send.back.confirm",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _send_back(self, reason):
        """to_commit → to_verify (ผู้ยืนยันงบประมาณ) / to_verify → draft
        (ผู้ตรวจสอบคำขอ). No commitment exists before ยืนยันงบประมาณ, so
        nothing is released. The reason rides on the state tracking message."""
        self.ensure_one()
        step = self.state
        if self.state == "to_commit":
            group, target = "agx_approval.group_approval_budget_commit", "to_verify"
        elif self.state == "to_verify":
            group, target = "agx_approval.group_approval_verify", "draft"
        else:
            raise UserError(
                _("ตีกลับได้เฉพาะสถานะ 'รอตรวจสอบข้อมูล' หรือ 'รอยืนยันงบประมาณ'")
            )
        if not self.env.user.has_group(group):
            raise UserError(_("คุณไม่มีสิทธิ์ตีกลับคำขอในสถานะนี้"))
        self._track_set_log_message(
            tools.plaintext2html(_("ตีกลับ: %s") % reason)
        )
        self.state = target
        self._mark_sent_back(step)
        return True

    def action_submit(self):
        for record in self:
            if record.state != "to_commit":
                raise UserError(_("Only To Commit requests can be submitted."))
            record.state = "to_send"
        return True

    def action_approve(self):
        """Internal approval fallback for installations without the Sarabun
        bridge. When agx_approval_sarabun is installed the request is approved
        by the Sarabun document outcome instead (see _on_sarabun_completed).

        Once approved the request's own work is done: it rests in ``approved``
        (open for disbursement) until finance closes it (ADR-0010)."""
        for record in self:
            if record.state not in ("to_send", "sent"):
                raise UserError(
                    _("Only submitted requests can be approved.")
                )
            record.state = "approved"
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
        if self.state not in ("to_verify", "to_commit", "to_send"):
            raise UserError(
                _(
                    "ดึงกลับได้เฉพาะสถานะ 'รอตรวจสอบข้อมูล', 'รอยืนยันงบประมาณ' "
                    "หรือ 'รอส่งขออนุมัติ'"
                )
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

    def _get_budget_commitment_extra_kwargs(self):
        """Extra kwargs forwarded to _create_budget_commitment().
        Override in bridge modules to inject e.g. operating_unit_id."""
        return {}

    def _advance_after_reserved(self):
        """Fired once a commitment is attached to the request — reserved new or
        drawn. Base always proceeds through the normal approval routing
        (→ to_send). A bridge may override this to skip routing instead — e.g.
        a project-funded expense whose spending was already cleared upstream."""
        return self.action_submit()

    def action_reserve_budget(self):
        """ยืนยันงบประมาณ (to_commit): either draw an existing reservation or
        reserve anew."""
        self.ensure_one()
        if self.state != "to_commit":
            raise UserError(_("ยืนยันงบประมาณได้เฉพาะสถานะ 'รอยืนยันงบประมาณ'"))
        if not self.env.user.has_group("agx_approval.group_approval_budget_commit"):
            raise UserError(_("คุณไม่มีสิทธิ์ยืนยันงบประมาณ"))

        # Draw-down mode: the user picked an existing ใบจองงบประมาณ. Adopt it
        # instead of creating a new commitment (ADR-0010).
        if self.reservation_commitment_id:
            return self._action_draw_from_reservation()

        # Chose a draw-down mode (anything but "normal") but picked nothing: say
        # so, instead of falling through to reserve-new and complaining about
        # the dimensions the mode switch deliberately cleared.
        if self.budget_selection_mode != "normal":
            raise UserError(_("กรุณาเลือกใบจองงบประมาณที่ต้องการหยิบไปใช้"))

        # รหัสงบประมาณ / มิติทางบัญชี ไม่บังคับกรอกในฟอร์ม — ตรวจครบที่เดียว
        # ตอนกดจองงบประมาณ (budget engine จับคู่แบบครบทุกมิติหรือไม่มีเลย)
        missing = []
        if not self.budget_account_id:
            missing.append(_("รหัสงบประมาณ"))
        if not self.department_analytic_id:
            missing.append(_("ส่วนงาน"))
        if not self.source_analytic_id:
            missing.append(_("แหล่งเงิน"))
        if not self.fund_analytic_id:
            missing.append(_("กองทุน"))
        if not self.activity_analytic_id:
            missing.append(_("กิจกรรม"))
        if missing:
            raise UserError(
                _("กรุณาระบุข้อมูลงบประมาณให้ครบก่อนจองงบประมาณ: %s")
                % ", ".join(missing)
            )

        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                agx_exception_action="action_reserve_budget"
            )._popup_exceptions()

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
                **self._get_budget_commitment_extra_kwargs(),
            )
            self.message_post(
                body=_("Budget reserved: %s for amount %s") % (commitment.name, amount)
            )
            self._advance_after_reserved()
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

    def _action_draw_from_reservation(self):
        """Draw down an existing reservation (ใบจองงบประมาณ) instead of reserving.

        Adopts the reservation's budget code and full dimension distribution —
        locked onto the request and its lines — links it as the request's
        commitment, and submits the request exactly like the reserve-new path. No
        new reservation is created: the money is already locked; obligate/consume
        happen downstream at the disbursement (ADR-0010). The request keeps the
        ปีงบประมาณ the user chose; the shared commitment carries the fiscal year
        it was reserved in. The plan total is checked against what the slip
        currently has left (``excep_draw_exceeds_available``) — a blocking
        exception, since drawing more than is available would silently overdraw
        a commitment that may be shared with other documents."""
        self.ensure_one()
        commitment = self.reservation_commitment_id
        if commitment.state not in ("reserved", "partial"):
            raise UserError(
                _("ใบจองงบประมาณ %s ไม่อยู่ในสถานะที่หยิบไปใช้ได้") % commitment.name
            )
        self._check_drawable_commitment(commitment)
        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                agx_exception_action="action_reserve_budget"
            )._popup_exceptions()
        self.write(
            {
                "budget_commitment_id": commitment.id,
                "budget_account_id": commitment.account_id.id,
                "analytic_distribution": commitment.analytic_distribution or False,
            }
        )
        if (
            self.line_ids
            and commitment.analytic_distribution
            and "analytic_distribution" in self.line_ids._fields
        ):
            self.line_ids.update(
                {"analytic_distribution": commitment.analytic_distribution}
            )
        self.message_post(
            body=_("หยิบใบจองงบประมาณ %s มาใช้ (draw down)") % commitment.name
        )
        self._advance_after_reserved()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
            "context": self.env.context,
        }

    def _check_drawable_commitment(self, commitment):
        """Block drawing a reservation this request must not use: a plan/project
        shared commitment (drawn only through their create-from-source flows,
        ADR-0006/0007) or a budget code this request could not itself select
        (approval-eligible expense code, ADR-0004)."""
        for fname, label in (
            ("procurement_plan_id", _("แผนจัดซื้อจัดจ้าง")),
            ("kmitl_project_id", _("โครงการ")),
        ):
            if fname in commitment._fields and commitment[fname]:
                raise UserError(
                    _("ใบจองงบประมาณของ%sต้องหยิบผ่านเอกสารต้นทางเท่านั้น") % label
                )
        if not self.env["budget.account"].search_count(
            self._reservation_account_domain()
            + [("id", "=", commitment.account_id.id)]
        ):
            raise UserError(
                _("รหัสงบประมาณของใบจองที่เลือกไม่สามารถใช้กับเอกสารนี้ได้")
            )
        return True

    @api.onchange("reservation_commitment_id")
    def _onchange_reservation_commitment_id(self):
        """Preview the picked reservation's budget code on the live form. The
        dimension distribution is written server-side on draw-down, not here —
        re-assigning analytic_distribution in an onchange wipes it on the unsaved
        record (its compute is a no-op)."""
        if self.reservation_commitment_id:
            self.budget_account_id = self.reservation_commitment_id.account_id.id

    @api.onchange("budget_selection_mode")
    def _onchange_budget_selection_mode(self):
        """Clear every budget-selection input on any mode switch.

        ``budget_selection_mode`` is a **UI affordance only** — the server still
        keys draw-down off the presence of ``reservation_commitment_id``
        (ADR-0010), never off this field. Leaving a prior mode's input filled
        would make the form say one thing and the reserve action do another: a
        stale chart selection under a draw-down mode, or a stale slip under
        "ใช้เงินจากแผน" that would silently draw instead of reserving.
        """
        self.reservation_commitment_id = False
        self.budget_account_id = False
        self.analytic_distribution = False

    def _cancel_budget_commitment(self):
        """A drawn reservation belongs to its owner, never to this request — detach
        instead of cancelling when this request drew an existing reservation
        (ADR-0010)."""
        self.ensure_one()
        if self.reservation_commitment_id:
            self.write(
                {"budget_commitment_id": False, "reservation_commitment_id": False}
            )
            return True
        return super()._cancel_budget_commitment()

    @api.depends(
        "state",
        "budget_commitment_id",
        "budget_commitment_id.state",
    )
    def _compute_is_budget_editable(self):
        # Means "budget selection is still open on this request", which is also
        # exactly when a reservation may be picked — so the reservation field
        # rides on this rather than re-listing states (they come from several
        # modules). Drawing an existing reservation does not close selection: the
        # user must be able to un-pick. The chart picker is hidden view-side
        # while a reservation is picked, since dimensions then come from it.
        # Each step's own role edits: ผู้ตรวจสอบคำขอ at to_verify, ผู้ยืนยัน
        # งบประมาณ at to_commit (ADR-0008).
        user = self.env.user
        can_edit = {
            "to_verify": user.has_group("agx_approval.group_approval_verify"),
            "to_commit": user.has_group("agx_approval.group_approval_budget_commit"),
        }
        for rec in self:
            if rec.state in can_edit and (
                not rec.budget_commitment_id
                or rec.budget_commitment_id.state == "cancel"
            ):
                rec.is_budget_editable = can_edit[rec.state]
            else:
                rec.is_budget_editable = rec.state == "draft"

    @api.depends("state", "budget_commitment_id")
    def _compute_hide_reserve_budget_button(self):
        for rec in self:
            if rec.state == "to_commit" and (
                not rec.budget_commitment_id
                or rec.budget_commitment_id.state == "cancel"
            ):
                rec.hide_reserve_budget_button = False
            else:
                rec.hide_reserve_budget_button = True

    @api.depends("state")
    def _compute_is_plan_editable(self):
        """The plan (expense lines, participants, header) stays editable until
        the request is sent for approval — i.e. through draft, รอตรวจสอบข้อมูล,
        รอยืนยันงบประมาณ and รอส่งขออนุมัติ. agx_approval_sarabun widens this to a Sarabun-returned
        request (edit everything except budget)."""
        for rec in self:
            rec.is_plan_editable = rec.state in (
                "draft", "to_verify", "to_commit", "to_send"
            )

    @api.depends("name")
    def _compute_is_number_assigned(self):
        # "/" is the placeholder a request carries until action_to_verify mints
        # its number. Kept untranslated on purpose — see the ``name`` field.
        for rec in self:
            rec.is_number_assigned = bool(rec.name and rec.name != "/")

    @api.depends("line_ids.total_amount")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped("total_amount"))
