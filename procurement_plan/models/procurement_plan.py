import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


MONTH_SELECTION = [
    ("1", "January"),
    ("2", "February"),
    ("3", "March"),
    ("4", "April"),
    ("5", "May"),
    ("6", "June"),
    ("7", "July"),
    ("8", "August"),
    ("9", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]


class ProcurementPlan(models.Model):
    _name = "procurement.plan"
    _description = "Procurement Plan"
    _inherit = ["mail.thread", "analytic.mixin"]
    _check_company_auto = True
    _rec_name = "description"
    _rec_names_search = ["name", "description"]
    _order = "name desc"

    READONLY_STATES = {
        "to_verify": [("readonly", True)],
        "in_progress": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        required=True,
        states=READONLY_STATES,
    )
    name = fields.Char(
        string="รหัสเอกสาร",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
        default="/",
    )
    description = fields.Char(
        string="ชื่อรายการ",
        required=True,
        tracking=True,
        states=READONLY_STATES,
        help="Fill the details include unit",
    )
    amount = fields.Integer(
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    unit = fields.Char(
        "Unit of Measure",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    total_price = fields.Float(
        "วงเงินรวม",
        store=True,
        readonly=False,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "แบบร่าง"),
            ("to_verify", "รอตรวจสอบข้อมูล"),
            ("verified", "รอดำเนินการ"),
            ("in_progress", "อยู่ในระหว่างดำเนินการ"),
            ("done", "จัดซื้อจัดจ้างเสร็จสิ้น"),
            ("cancel", "ยกเลิก"),
        ],
        string="Status",
        readonly=True,
        copy=False,
        default="draft",
        tracking=True,
    )
    # A soft-deleted plan (ADR-0005) is archived together with its analytic
    # account; Reset to Draft brings both back with the same number.
    active = fields.Boolean(default=True, tracking=True)
    note = fields.Text("Notes", tracking=True)
    purchase_request_eta = fields.Selection(
        MONTH_SELECTION,
        "Purchase Request (ETA)",
        tracking=True,
    )
    procurement_announcement_eta = fields.Selection(
        MONTH_SELECTION, "Procurement Announcement (ETA)", tracking=True
    )
    approval_signing_eta = fields.Selection(
        MONTH_SELECTION,
        "Approval Signing (ETA)",
        tracking=True,
    )
    contract_order_signing_eta = fields.Selection(
        MONTH_SELECTION, "Contract Order Signing (ETA)", tracking=True
    )
    acceptance_eta = fields.Selection(
        MONTH_SELECTION,
        "Acceptance (ETA)",
        tracking=True,
    )
    payment_ids = fields.One2many(
        comodel_name="procurement.plan.payment",
        inverse_name="procurement_plan_id",
        copy=True,
    )
    user_id = fields.Many2one(
        string="User",
        comodel_name="res.users",
        copy=False,
        default=lambda self: self.env.user,
        store=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    responsible_id = fields.Many2one(
        string="เจ้าหน้าที่ผู้รับผิดชอบ",
        comodel_name="res.users",
        domain=[("share", "=", False)],
        index=True,
        tracking=True,
        states={"done": [("readonly", True)], "cancel": [("readonly", True)]},
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )

    can_edit_description = fields.Boolean(
        store=False, compute="_compute_can_edit_description"
    )

    @api.depends("state")
    def _compute_can_edit_description(self):
        for record in self:
            record.can_edit_description = record.state in (
                "draft",
                "to_verify",
                "verified",
                "in_progress",
            )

    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        copy=False,
        inverse="_inverse_analytic_account_id",
        ondelete="set null",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Analytic account to which this procurement plan. \n"
        "Track the costs and revenues of your procurement plan by setting this analytic account on your related documents (e.g. budgetings, purchase requests, purchase orders etc.).",
    )
    analytic_account_balance = fields.Monetary(related="analytic_account_id.balance")

    def copy(self, default=None):
        default = dict(default or {})
        # analytic_account_id has copy=False, but analytic_distribution (JSON) is
        # copied as-is and still contains the old minted account's id.  Strip it so
        # the duplicate starts clean; a fresh account is minted on action_send_to_verify.
        if self.analytic_account_id:
            dist = dict(self.analytic_distribution or {})
            dist.pop(str(self.analytic_account_id.id), None)
            default["analytic_distribution"] = dist or False
        # Keep ชื่อรายการ unique on duplicate: append " (copy)" until it no longer
        # collides with an existing plan (repeat so copying a copy doesn't clash).
        if "description" not in default and self.description:
            copy_name = self.description
            while self.with_context(active_test=False).search_count(
                [("description", "=", copy_name)]
            ):
                copy_name = _("%s (copy)") % copy_name
            if copy_name != self.description:
                default["description"] = copy_name
        return super().copy(default)

    def unlink(self):
        """ลบแผน (ADR-0005), Odoo's own Delete: a plan whose analytic has no
        Ledger Footprint goes for good together with the analytic; one that is
        part of the budget history is soft-deleted (``action_cancel``) instead,
        so it stays archived and can be revived."""
        for plan in self:
            plan._check_deletable()
        soft = self.filtered(lambda p: p._must_soft_delete())
        soft.action_cancel()
        hard = self - soft
        analytics = hard.analytic_account_id
        result = super(ProcurementPlan, hard).unlink()
        analytics.sudo().unlink()
        return result

    def _must_soft_delete(self):
        """Whether the plan is part of the history and so may only be
        soft-deleted: its analytic has a Ledger Footprint."""
        self.ensure_one()
        return bool(
            self.analytic_account_id
            and self.analytic_account_id._has_ledger_footprint(exclude=self)
        )

    def _check_plan_manager(self, action):
        """Close, Reset to Draft and deleting a numbered plan are plan-manager
        acts (ADR-0002)."""
        if self.env.su or self.env.user.has_group(
            "procurement_plan.group_procurement_plan_manager"
        ):
            return
        raise UserError(_("%s ได้เฉพาะผู้จัดการแผนจัดซื้อจัดจ้างเท่านั้น") % action)

    def _check_deletable(self):
        """Every guard of ลบแผน (ADR-0005): deleting never moves money and never
        strands a document that still points at the plan."""
        self.ensure_one()
        if self.name and self.name != "/":
            self._check_plan_manager(_("ลบแผนที่มีเลขที่แล้ว (%s)") % self.name)
        if self.state == "done":
            raise UserError(_("ไม่สามารถลบแผนที่ปิดแล้ว (%s)") % self.name)
        if self._has_spent():
            raise UserError(
                _("แผน %s มีการใช้จ่ายงบประมาณแล้ว ลบไม่ได้ กรุณาปิดแผนแทน") % self.name
            )
        reasons = self._get_held_money_reasons()
        if reasons:
            raise UserError(
                _("ไม่สามารถลบแผน %s ได้ เนื่องจาก:\n%s\nกรุณาโอนคืนงบลอยให้เหลือ 0 บาทก่อน")
                % (self.name, "\n".join("- %s" % reason for reason in reasons))
            )
        open_documents = self._get_open_downstream_documents()
        if open_documents:
            raise UserError(
                _("ไม่สามารถลบแผน %s ได้ เนื่องจากยังมีเอกสารที่อ้างถึงแผนนี้:\n%s")
                % (self.name, "\n".join("- %s" % doc for doc in open_documents))
            )

    def _has_spent(self):
        """Hook: whether the plan has obligated or consumed money (budget layer)."""
        self.ensure_one()
        return False

    def _get_held_money_reasons(self):
        """Hook: why the plan still holds money (Held Money, budget layer).
        Empty when it holds none."""
        self.ensure_one()
        return []

    def _get_open_downstream_documents(self):
        """Hook: labels of the documents still open on this plan (purchase
        requests, purchase orders, disbursement requests) — extended by the
        bridges that own them. Blocks ปิดแผน and ลบแผน."""
        self.ensure_one()
        return []

    def _track_subtype(self, init_values):
        self.ensure_one()
        if "state" in init_values:
            return self.env.ref("procurement_plan.mt_plan_state")
        return super()._track_subtype(init_values)

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        """The Responsible follows the plan like ``user_id`` does, so they are
        told of every status change (สถานะแผน)."""
        res = super()._message_auto_subscribe_followers(
            updated_values, default_subtype_ids
        )
        user = self.env["res.users"].sudo().browse(updated_values.get("responsible_id"))
        if user.exists() and user.active:
            res.append(
                (
                    user.partner_id.id,
                    default_subtype_ids,
                    "mail.message_user_assigned" if user != self.env.user else False,
                )
            )
        return res

    def write(self, vals):
        res = super().write(vals)
        # Keep the plan's analytic account label in step with its description —
        # the description is minted onto the analytic at ส่งเข้ารอจัดสรรงบประมาณ
        # and stays editable in draft/to_verify, so a later rename must follow
        # through to the dimension.
        if vals.get("description"):
            for record in self:
                if (
                    record.analytic_account_id
                    and record.analytic_account_id.name != record.description
                ):
                    record.analytic_account_id.name = record.description
        return res

    @api.model
    def _create_analytic_account_from_values(self, values):
        analytic_account = self.env["account.analytic.account"].create(
            {
                "name": values.get("name", _("Unknown Analytic Account")),
                "code": values.get("code"),
                "company_id": self.env.company.id,
                "partner_id": values.get("partner_id"),
                "plan_id": self.env.ref(
                    "procurement_plan.analytic_plan_procurement_plan",
                    raise_if_not_found=True,
                ).id,
            }
        )
        return analytic_account

    def action_send_to_verify(self):
        """draft → to_verify: assign the sequence number and mint the plan's
        analytic account. Sequence is consumed here (not on save) so draft
        records that are deleted never waste a number."""
        for record in self.sorted("id"):
            if not record.name or record.name == "/":
                # The document number's year must come from the ปีงบประมาณ, not
                # today. In the use_date_range path %(year_be)s reads the
                # effective date from the ``ir_sequence_date`` context (the
                # date_range only drives the per-year counter reset), so pin both
                # to the fiscal year's end date — its Gregorian year + 543 is the
                # BE fiscal-year number (e.g. FY 2570 ends 2027 → 2570).
                fiscal_date = record.account_fiscal_year_id.date_to
                record.name = (
                    self.env["ir.sequence"]
                    .with_context(ir_sequence_date=fiscal_date)
                    .next_by_code(
                        "procurement.plan",
                        sequence_date=fiscal_date,
                    )
                    or "/"
                )
        self.write({"state": "to_verify"})
        for record in self:
            if not record.analytic_account_id:
                analytic_account = record._create_analytic_account_from_values(
                    {
                        "name": record.description,
                        "code": record.name,
                    }
                )
                record.analytic_account_id = analytic_account.id

    def action_verify(self):
        """to_verify → verified: plain "ยืนยัน" at the core level. The budget
        layer overrides ``_on_verify`` to reserve the plan's budget instead."""
        if self.state not in ("to_verify",):
            raise UserError(_("Record must be in to_verify state to be verified."))
        self._on_verify()
        self.write({"state": "verified"})

    def _on_verify(self):
        """No-op hook. Budget layer reserves the plan's budget here."""
        return

    def action_in_progress(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        """ปิดแผน (ADR-0005): ``in_progress`` → ``done``, by hand only. Waits for
        every downstream document to finish, then lets the budget layer return
        the unspent reservation (``_on_close``)."""
        self._check_plan_manager(_("ปิดแผน"))
        for plan in self:
            if plan.state != "in_progress":
                raise UserError(_("ปิดแผนได้เฉพาะแผนที่อยู่ในระหว่างดำเนินการ"))
            open_documents = plan._get_open_downstream_documents()
            if open_documents:
                raise UserError(
                    _("ไม่สามารถปิดแผน %s ได้ เนื่องจากยังมีเอกสารค้างดำเนินการ:\n%s")
                    % (plan.name, "\n".join("- %s" % doc for doc in open_documents))
                )
        self.write({"state": "done"})
        self._on_close()

    def _on_close(self):
        """No-op hook. Budget layer returns the unspent reservation here."""
        return

    def action_reset_to_draft(self):
        self._check_plan_manager(_("กลับเป็นแบบร่าง"))
        if self.filtered(lambda p: p.state not in ("to_verify", "verified", "cancel")):
            raise UserError(_("กลับเป็นแบบร่างได้เฉพาะแผนที่รอจัดสรร/รอดำเนินการ หรือแผนที่ถูกลบ"))
        self._on_reset()
        # A soft-deleted plan comes back with its analytic account (ADR-0005).
        self.write({"state": "draft", "active": True})
        self.analytic_account_id.sudo().filtered(lambda a: not a.active).write(
            {"active": True}
        )

    def _on_reset(self):
        """No-op hook. Budget layer releases an untouched reservation here."""
        return

    def action_cancel(self):
        """Soft delete (ADR-0005): → ``cancel`` and archive the plan and its
        analytic account, for a plan whose analytic is part of the budget
        history. No button of its own — reached through ลบแผน (``unlink``),
        only once ``_check_deletable`` passes; Reset to Draft revives both."""
        for plan in self:
            plan._check_deletable()
        self._on_cancel()
        self.write({"state": "cancel", "active": False})
        self.analytic_account_id.sudo().filtered("active").write({"active": False})

    def _on_cancel(self):
        """No-op hook. Budget layer releases an untouched reservation here."""
        return

    can_edit = fields.Boolean(compute="_compute_can_edit")

    @api.depends("state")
    def _compute_can_edit(self):
        for rec in self:
            if rec.state == "draft":
                rec.can_edit = True
            else:
                rec.can_edit = False

    def name_get(self):
        res = []
        for rec in self:
            source_name = (
                rec.source_analytic_id.name
                if rec.source_analytic_id
                else _("ไม่ระบุแหล่งเงิน")
            )
            res.append(
                (
                    rec.id,
                    _(f"[%s] %s งบประมาณ {rec.total_price:,.2f} บาท - %s")
                    % (rec.name, rec.description, source_name),
                )
            )
        return res

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=True,
        tracking=True,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=True,
        tracking=True,
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse="_inverse_fund_analytic",
        domain=[("root_plan_id.code", "=", "funds")],
        store=False,
        compute_sudo=True,
        tracking=True,
        states=READONLY_STATES,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse="_inverse_source_analytic",
        domain=[("root_plan_id.code", "=", "sources")],
        store=True,
        tracking=True,
        states=READONLY_STATES,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
        "procurement_plan": "analytic_account_id",
    }

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
        """Update distribution when fund changes"""
        for line in self:
            line._update_analytic_distribution("sources")

    def _inverse_analytic_account_id(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("procurement_plan")
