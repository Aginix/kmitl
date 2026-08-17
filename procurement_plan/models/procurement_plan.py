import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

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
        compute="_compute_name",
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
        comodel_name="procurement.plan.payment", inverse_name="procurement_plan_id"
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
            record.can_edit_description = record.state in ("draft", "to_verify")

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

    def unlink(self):
        # Delete the empty related analytic account
        analytic_accounts_to_delete = self.env["account.analytic.account"]
        for record in self:
            if record.analytic_account_id and not record.analytic_account_id.line_ids:
                analytic_accounts_to_delete |= record.analytic_account_id
        result = super().unlink()
        analytic_accounts_to_delete.unlink()
        return result

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

    @api.depends("state", "name", "account_fiscal_year_id")
    def _compute_name(self):
        self = self.sorted(lambda m: m.id)

        for record in self:
            if record.state == "cancel":
                continue

            record_has_name = record.name and record.name != _("New")
            if not record_has_name:
                record.name = self.env["ir.sequence"].next_by_code(
                    "procurement.plan",
                    sequence_date=record.account_fiscal_year_id.date_to,
                ) or _("New")

    def action_send_to_verify(self):
        """draft → to_verify: mint the plan's analytic account (idempotent, D1
        for the standalone plan — pure account.analytic, no budget needed)."""
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

    def _on_reset(self):
        """No-op hook. Budget layer releases an untouched reservation here."""
        return

    def action_cancel(self):
        self._on_cancel()
        self.write({"state": "cancel"})

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
        domain=[("root_plan_id.code", "=", "activities")],
        store=True,
        tracking=True,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        domain=[("root_plan_id.code", "=", "departments")],
        store=True,
        tracking=True,
        states=READONLY_STATES,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        domain=[("root_plan_id.code", "=", "funds")],
        store=True,
        tracking=True,
        states=READONLY_STATES,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
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

    def _inverse_analytic_account_id(self):
        """Update distribution when source changes"""
        for line in self:
            line._update_analytic_distribution("procurement_plan")
