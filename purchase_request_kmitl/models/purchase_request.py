from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    partner_id_domain = fields.Binary(
        compute="_compute_partner_id_domain",
        readonly=True,
        store=False,
    )

    @api.depends("payment_type")
    def _compute_partner_id_domain(self):
        for rec in self:
            rec.partner_id_domain = []

    state = fields.Selection(
        selection_add=[
            ("to_verify", "To be verified"),
            ("to_approve",),
            ("cancelled", "Cancelled"),
            ("returned", "Returned"),
        ],
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        ondelete={
            "to_verify": "set default",
            "cancelled": "set default",
            "returned": "set default",
        },
    )

    is_purchase_request = fields.Boolean(compute="_compute_is_purchase_request")
    can_request = fields.Boolean(compute="_compute_can_request")

    line_ids = fields.One2many(
        states={
            "draft": [("readonly", False)],
            "returned": [("readonly", False)],
        },
    )
    procurement_type_id = fields.Many2one(
        comodel_name="procurement.type",
        string="Procurement Type",
        ondelete="restrict",
        index=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        index=True,
    )
    procurement_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Procurement Committees",
        domain=[("committee_type", "=", "procurement")],
        copy=True,
    )
    work_acceptance_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Acceptance Committees",
        domain=[("committee_type", "=", "work_acceptance")],
        copy=True,
    )
    payment_type = fields.Selection(
        [("direct", "Direct paid"), ("advance", "Advance"), ("prepaid", "Prepaid")],
        tracking=True,
    )

    @api.onchange("payment_type")
    def _onchange_payment_type_clear_vendor_fields(self):
        if self.payment_type and self.payment_type != "direct":
            self.partner_id = False
            self.vat_included = "exclusive"
            self.tax_id = False

    assigned_to = fields.Many2one(
        string="Purchase Representative",
        copy=False,
    )
    verified_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    approved_by = fields.Many2one(
        comodel_name="res.users",
        index=True,
        copy=False,
        tracking=True,
    )
    date_start = fields.Date(
        copy=False,
        default=False,
    )
    date_verified = fields.Date(
        string="Verified Date",
        copy=False,
    )
    date_approved = fields.Date(
        string="Approved Date",
        copy=False,
    )
    partner_id = fields.Many2one("res.partner", tracking=True)

    # construction
    is_construction = fields.Boolean(string="Construction", readonly=True)
    title = fields.Char(string="Title", tracking=True)
    requesting_department_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Requesting Department",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        help="ส่วนงานผู้ขอให้จัดหา — ไม่จำเป็นต้องตรงกับส่วนงานของงบประมาณ",
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        default=lambda self: self._default_account_fiscal_year_id(),
    )

    @api.model
    def _default_account_fiscal_year_id(self):
        """ปีงบปัจจุบัน (ตามวันนี้) เป็นค่าตั้งต้น.

        ทุก flow ด้านงบใช้ปีงบนี้อยู่แล้ว (จอง/หยิบใบจอง/ออกเลขที่ พจ.) การเว้นว่างทำให้
        dropdown ใบจองที่กรองตามปีงบไม่ขึ้นรายการ และเลขที่ พจ. หล่นไปใช้ปีปฏิทินแทนปีงบ."""
        today = fields.Date.context_today(self)
        return self.env["account.fiscal.year"].search(
            [
                ("date_from", "<=", today),
                ("date_to", ">=", today),
                ("company_id", "in", [self.env.company.id, False]),
            ],
            limit=1,
        )

    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        domain=[("res_model", "=", "purchase.request")],
        string="Document Attachments",
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        copy=False,
        default=lambda self: self.env.user,
        index=True,
    )
    tor_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="TOR Committees",
        domain=[("committee_type", "=", "tor_committee")],
        copy=True,
    )
    price_determine_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Price Determine Committees",
        domain=[("committee_type", "=", "price_determine")],
        copy=True,
    )
    evaluation_committee_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Evaluation Committees",
        domain=[("committee_type", "=", "evaluation")],
        copy=True,
    )
    work_supervisor_ids = fields.One2many(
        comodel_name="procurement.committee",
        inverse_name="request_id",
        string="Work Supervisors",
        domain=[("committee_type", "=", "work_supervisor")],
        copy=True,
    )
    hide_create_po_button = fields.Boolean(compute="_hide_create_po_button")
    can_reset_to_draft = fields.Boolean(compute="_compute_can_reset_to_draft")
    can_owner_act = fields.Boolean(compute="_compute_can_act")
    can_team_act = fields.Boolean(compute="_compute_can_act")

    def _compute_is_purchase_request(self):
        for rec in self:
            rec.is_purchase_request = rec._name == "purchase.request"

    @api.depends("requested_by")
    def _compute_can_request(self):
        current_user = self.env.user
        is_manager = current_user.has_group(
            "purchase_request.group_purchase_request_manager"
        )
        is_admin = current_user.has_group("base.group_erp_manager")
        for rec in self:
            own_by_me = rec.requested_by.id == current_user.id
            rec.can_request = own_by_me or is_manager or is_admin

    def _is_pr_owner(self):
        """ผู้จัดทำ: the PR's ``user_id``."""
        self.ensure_one()
        return self.env.su or self.user_id == self.env.user

    def _is_pr_team(self):
        """ผู้จัดทำ / ธุรการ (who created the PR) / พัสดุ (Purchase User)."""
        self.ensure_one()
        return (
            self._is_pr_owner()
            or self.create_uid == self.env.user
            or self.env.user.has_group("purchase.group_purchase_user")
        )

    @api.depends("user_id", "create_uid")
    def _compute_can_act(self):
        for rec in self:
            rec.can_owner_act = rec._is_pr_owner()
            rec.can_team_act = rec._is_pr_team()

    def _check_is_owner(self):
        if any(not rec._is_pr_owner() for rec in self):
            raise UserError(
                _("เฉพาะผู้จัดทำแบบขอให้จัดหา (พ.1) เท่านั้นที่ดำเนินการขั้นนี้ได้")
            )

    def _check_is_team(self):
        if any(not rec._is_pr_team() for rec in self):
            raise UserError(
                _(
                    "เฉพาะผู้จัดทำ ธุรการ หรือพัสดุของแบบขอให้จัดหา (พ.1) "
                    "เท่านั้นที่ดำเนินการขั้นนี้ได้"
                )
            )

    @api.depends("state")
    def _compute_is_editable(self):
        super()._compute_is_editable()
        editable_states = ("draft", "to_verify", "returned")
        for record in self:
            record.is_editable = record.state in editable_states

    def button_to_verify(self):
        self.ensure_one()
        self._check_is_owner()
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        vals = {"state": "to_verify"}
        if not self.date_start:
            vals["date_start"] = fields.Date.context_today(self)
        self.write(vals)

    def _check_step_group(self, state, group, message):
        """Raise unless the user holds ``group`` for records at ``state``.

        Each step of the พ.1 is held by its own group (ADR-0010) and the view
        gate alone is bypassable over RPC. Superuser mode (hooks, sudo'ed
        programmatic flows) passes."""
        if (
            not self.env.su
            and any(rec.state == state for rec in self)
            and not self.env.user.has_group(group)
        ):
            raise UserError(message)

    def _check_can_verify(self):
        self._check_step_group(
            "to_verify",
            "purchase_request_kmitl.group_purchase_request_verify",
            _("เฉพาะผู้ตรวจสอบแบบขอให้จัดหา (พ.1) เท่านั้นที่ดำเนินการขั้นนี้ได้"),
        )

    def _mark_verified(self):
        """Stamp who pressed ตรวจสอบ, and when (ADR-0010)."""
        self.write(
            {
                "verified_by": self.env.user.id,
                "date_verified": fields.Date.context_today(self),
            }
        )

    def button_to_approve(self):
        self._check_can_verify()
        to_verify = self.filtered(lambda r: r.state == "to_verify")
        res = super().button_to_approve()
        # Only those that actually advanced: an exception popup returns
        # without moving the state.
        to_verify.filtered(lambda r: r.state != "to_verify")._mark_verified()
        return res

    def button_draft(self):
        self._check_can_reset_to_draft()
        self.write({"verified_by": False, "date_verified": False})
        return super().button_draft()

    def _check_can_reset_to_draft(self):
        """ดึงกลับ → ร่าง is gated per state by ``can_reset_to_draft``. Other
        states (draft itself, post-approval) keep the base behaviour."""
        if self.env.su:
            return
        pull_back_states = ("to_verify", "to_verify_budget", "to_approve", "returned")
        for rec in self:
            if rec.state in pull_back_states and not rec.can_reset_to_draft:
                raise UserError(_("คุณไม่มีสิทธิ์ดึงกลับคำขอ (พ.1) %s") % rec.name)

    @api.depends("state", "user_id", "create_uid")
    def _compute_can_reset_to_draft(self):
        for rec in self:
            if rec.state == "to_verify":
                rec.can_reset_to_draft = rec._is_pr_owner()
            elif rec.state in ("to_approve", "returned"):
                rec.can_reset_to_draft = rec._is_pr_team()
            else:
                rec.can_reset_to_draft = False

    @api.depends("state")
    def _hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = not (
                rec.state in ("approved", "in_progress") and rec.purchase_count == 0
            )

    def get_estimated_cost_currency(self, date=False):
        """Return the total estimated cost across all lines."""
        self.ensure_one()
        return sum(self.line_ids.mapped("estimated_cost"))

    def _apply_sarabun_approve_metadata(self):
        self.write(
            {
                "approved_by": self.env.user.id,
                "date_approved": fields.Date.context_today(self),
            }
        )

    def _transition_after_sarabun_approve(self):
        """Dispatch state transition after Sarabun completes routing.

        Overridden in purchase_request_egp (is_egp=True → in_egp) and
        purchase_request_approval (is_egp=False → in_approval + auto-PA).
        The base fallback writes 'approved' if neither branch is installed.
        """
        self._apply_sarabun_approve_metadata()
        self.write({"state": "approved"})

    def button_approved(self):
        self._apply_sarabun_approve_metadata()
        return super().button_approved()

    def button_cancel(self):
        self.ensure_one()
        self._check_can_cancel()
        return {
            "type": "ir.actions.act_window",
            "name": _("ยกเลิกคำขอ (พ.1)"),
            "res_model": "purchase.request.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _check_can_cancel(self):
        """Before Sarabun, only the ผู้จัดทำ cancels, and only from draft — a PR
        further along must be pulled back or returned to draft first. Post-approval
        states keep their existing Cancel."""
        if self.env.su:
            return
        pre_sarabun_states = (
            "to_verify",
            "to_verify_budget",
            "to_approve",
            "sent",
            "returned",
        )
        if any(rec.state in pre_sarabun_states for rec in self):
            raise UserError(
                _("ยกเลิกคำขอ (พ.1) ได้เฉพาะสถานะร่าง — กรุณาดึงกลับเป็นร่างก่อน")
            )
        self.filtered(lambda r: r.state == "draft")._check_is_owner()

    def _action_do_cancel(self, reason):
        self.ensure_one()
        body = _("ยกเลิกคำขอ (พ.1) %(pr)s เหตุผล: %(reason)s") % {
            "pr": self.name,
            "reason": reason,
        }
        self.message_post(body=body, subtype_xmlid="mail.mt_note")
        self.write({"state": "cancelled"})

    def button_return(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ตีกลับคำขอ (พ.1)"),
            "res_model": "purchase.request.return.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _action_do_return(self, reason=None, post_message=True):
        self.ensure_one()
        if post_message:
            body = _("ตีกลับคำขอ (พ.1) %(pr)s เหตุผล: %(reason)s") % {
                "pr": self.name,
                "reason": reason or "",
            }
            self.message_post(body=body, subtype_xmlid="mail.mt_note")
        self.write({"state": "returned"})

    def _action_do_return_to_draft(self, reason):
        """ตีกลับ ถอยทีละขั้น (ADR-0010): ผู้ตรวจสอบตีกลับ ``to_verify`` ไป draft."""
        self.ensure_one()
        self._check_can_verify()
        body = _("ตีกลับคำขอ (พ.1) %(pr)s เหตุผล: %(reason)s") % {
            "pr": self.name,
            "reason": reason,
        }
        self.message_post(body=body, subtype_xmlid="mail.mt_note")
        # The verifier is not the ผู้จัดทำ who owns ดึงกลับ; authority was checked above.
        return self.sudo().button_draft()
