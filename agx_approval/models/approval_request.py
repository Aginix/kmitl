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
        # An approval is not a procurement (ADR-0004): reserve against
        # non-procurement expense codes, not product-backed purchase codes.
        return [
            ("budgetable", "=", True),
            ("budget_type", "=", "expense"),
            ("purchase_ok", "=", False),
        ]

    def _reservation_account_domain(self):
        """Budget codes selectable in the reservation picker for this request.

        Non-procurement expense codes (ADR-0004) on top of the mixin's
        budgetable/expense baseline, so the picker cannot offer — and
        apply_reservation_selection cannot write — a code the request rejects.
        When the category pins a budget code, that code is the request's hard
        constraint (single choke point for picker, write-back, and draw-down).
        """
        domain = super()._reservation_account_domain() + self._domain_budget_account_id()
        if self.category_id.budget_account_id:
            domain += [("id", "=", self.category_id.budget_account_id.id)]
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
            return self.category_id.name
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
            ("chart", "เลือกจากผังงบประมาณ (จองงบใหม่)"),
            ("reservation", "หยิบจากใบจองงบประมาณที่มีอยู่"),
        ],
        string="วิธีเลือกงบประมาณ",
        default="chart",
        copy=False,
        help=(
            "เลือกว่าจะจองงบใหม่โดยเลือกมิติจากผังงบประมาณ "
            "หรือหยิบใบจองงบประมาณที่หน่วยงานอื่นจองไว้ให้แล้วไปใช้"
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

    allowed_reservation_commitment_ids = fields.Many2many(
        "budget.commitment",
        compute="_compute_allowed_reservation_commitment_ids",
    )

    @api.depends("category_id", "state")
    def _compute_allowed_reservation_commitment_ids(self):
        for rec in self:
            rec.allowed_reservation_commitment_ids = self.env["budget.commitment"].search(
                rec._domain_reservation_commitment_id()
            )

    def _domain_reservation_commitment_id(self):
        """Reservations this request may draw down (phase-1 dropdown). OU
        visibility (owner or beneficiary unit) is enforced by the record rules
        (ADR-0011). Plan/project shared commitments are drawn only through their
        dedicated create-from-source flows (ADR-0006/0007), so they are excluded
        here — guarded by field existence since agx_approval does not depend on
        procurement_plan / kmitl_project."""
        domain = [
            ("state", "in", ("reserved", "partial")),
            ("available_to_obligate", ">", 0),
        ]
        Commitment = self.env["budget.commitment"]
        for fname in ("procurement_plan_id", "kmitl_project_id"):
            if fname in Commitment._fields:
                domain.append((fname, "=", False))
        account_ids = (
            self.env["budget.account"].search(self._reservation_account_domain()).ids
        )
        domain.append(("account_id", "in", account_ids))
        return domain

    def action_open_reservation_picker(self):
        """Browse the picker in only-selectable mode: the requester may pick only
        codes this request accepts (a category-pinned code, else the
        non-procurement baseline), so the picker collapses the ประเภทงบ chart to
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
        self.write({"state": "to_verify", "date": fields.Date.context_today(self)})
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
        """Reserve budget: either draw an existing reservation or reserve anew."""
        self.ensure_one()

        # Draw-down mode: the user picked an existing ใบจองงบประมาณ. Adopt it
        # instead of creating a new commitment (ADR-0010).
        if self.reservation_commitment_id:
            return self._action_draw_from_reservation()

        # Chose "หยิบจากใบจอง" but picked nothing: say so, instead of falling
        # through to reserve-new and complaining about the dimensions the mode
        # switch deliberately cleared.
        if self.budget_selection_mode == "reservation":
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

    def _action_draw_from_reservation(self):
        """Draw down an existing reservation (ใบจองงบประมาณ) instead of reserving.

        Adopts the reservation's budget code and full dimension distribution —
        locked onto the request and its lines — links it as the request's
        commitment, and submits the request exactly like the reserve-new path. No
        new reservation and no availability re-check: the money is already locked;
        obligate/consume happen downstream at the disbursement (ADR-0010). The
        request keeps the ปีงบประมาณ the user chose; the shared commitment carries
        the fiscal year it was reserved in."""
        self.ensure_one()
        commitment = self.reservation_commitment_id
        if commitment.state not in ("reserved", "partial"):
            raise UserError(
                _("ใบจองงบประมาณ %s ไม่อยู่ในสถานะที่หยิบไปใช้ได้") % commitment.name
            )
        self._check_drawable_commitment(commitment)
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
        self.action_submit()
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
        (non-procurement expense code, ADR-0004)."""
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
        """Clear whichever side of the choice is now inactive.

        ``budget_selection_mode`` is a **UI affordance only** — the server still
        keys draw-down off the presence of ``reservation_commitment_id``
        (ADR-0010), never off this field. Leaving the unused side filled would
        make the form say one thing and the reserve action do another: a stale
        chart selection under "หยิบจากใบจอง", or a stale slip under "เลือกจากผัง"
        that would silently draw instead of reserving.
        """
        if self.budget_selection_mode == "chart":
            self.reservation_commitment_id = False
        else:
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
        can_edit = self.env.user.has_group("budget.group_budget_commitment")
        for rec in self:
            if rec.state in ("to_verify") and (
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
