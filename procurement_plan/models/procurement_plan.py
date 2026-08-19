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
        default=lambda self: _("New"),
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
        comodel_name="procurement.plan.payment", inverse_name="procurement_plan_id", copy=True
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
            record.can_edit_description = record.state in ("draft", "to_verify", "verified", "in_progress")

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
        # Delete the empty related analytic account
        analytic_accounts_to_delete = self.env["account.analytic.account"]
        for record in self:
            if record.analytic_account_id and not record.analytic_account_id.line_ids:
                analytic_accounts_to_delete |= record.analytic_account_id
        result = super().unlink()
        analytic_accounts_to_delete.unlink()
        return result

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
            if not record.name or record.name == _("New"):
                # The document number's year must come from the ปีงบประมาณ, not
                # today. In the use_date_range path %(year_be)s reads the
                # effective date from the ``ir_sequence_date`` context (the
                # date_range only drives the per-year counter reset), so pin both
                # to the fiscal year's end date — its Gregorian year + 543 is the
                # BE fiscal-year number (e.g. FY 2570 ends 2027 → 2570).
                fiscal_date = record.account_fiscal_year_id.date_to
                record.name = self.env["ir.sequence"].with_context(
                    ir_sequence_date=fiscal_date
                ).next_by_code(
                    "procurement.plan",
                    sequence_date=fiscal_date,
                ) or _("New")
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
        self.write({"state": "done"})

    def action_reset_to_draft(self):
        self._on_reset()
        self.write({"state": "draft"})
        # Revive the plan's analytic dimension that action_cancel archived, so a
        # cancelled plan brought back to draft carries its account with it.
        self.analytic_account_id.filtered(lambda a: not a.active).write(
            {"active": True}
        )

    def _on_reset(self):
        """No-op hook. Budget layer releases an untouched reservation here."""
        return

    def action_cancel(self):
        self._on_cancel()
        self.write({"state": "cancel"})
        # Archive the plan's analytic dimension so a cancelled plan's account
        # stops showing up as a selectable มิติ; action_reset_to_draft revives it.
        self.analytic_account_id.filtered(lambda a: a.active).write(
            {"active": False}
        )

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
