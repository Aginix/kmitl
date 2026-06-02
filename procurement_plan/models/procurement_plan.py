import logging

from odoo.tools.misc import format_amount
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
        "new": [("readonly", True)],
        "on_hold": [("readonly", True)],
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
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        required=False,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("new", "New"),
            ("on_hold", "On Hold"),
            ("ready", "Ready"),
            ("in_progress", "In progress"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
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
            if record.state in ("draft", "new"):
                record.can_edit_description = True
            else:
                record.can_edit_description = False

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

    def write(self, vals):
        res = super().write(vals)
        if (
            "state" in vals
            and vals["state"] not in ("draft", "cancel")
            and not self.analytic_account_id
        ):
            analytic_account = self._create_analytic_account_from_values(
                {
                    "name": self.description,
                    "code": self.name,
                }
            )
            self.analytic_account_id = analytic_account.id
        return res

    @api.depends("state", "name")
    def _compute_name(self):
        self = self.sorted(lambda m: m.id)

        for record in self:
            if record.state == "cancel":
                continue

            record_has_name = record.name and record.name != _("New")
            if not record_has_name:
                record.name = self.env["ir.sequence"].next_by_code(
                    "procurement.plan"
                ) or _("New")

    def action_reset_to_draft(self):
        self._release_plan_commitment()
        self.write({"state": "draft"})

    def action_new(self):
        self.write({"state": "new"})

    def action_ready(self):
        if self.state not in ("new"):
            raise UserError(_("Record must be in new state to be set to ready."))
        if (
            not self.purchase_request_eta
            or not self.procurement_announcement_eta
            or not self.approval_signing_eta
            or not self.contract_order_signing_eta
            or not self.acceptance_eta
            or not self.procurement_method_id
        ):
            raise UserError(_("กรุณาระบุแผนการดำเนินงานให้เสร็จสิ้นทั้งหมด"))
        self._reserve_plan_commitment()
        self.write({"state": "ready"})

    def action_on_hold(self):
        self._release_plan_commitment()
        self.write({"state": "on_hold"})

    def action_in_progress(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        self.write({"state": "done"})

    def _reserve_plan_commitment(self):
        """Reserve one shared budget.commitment for the plan when it is made
        ready (D1). Idempotent: skips when an active (non-cancelled) commitment
        already exists. Blocks on insufficient budget unless budget.allow_negative
        is set. Downstream PR/PO/DR draw this single commitment down."""
        self.ensure_one()
        if self.budget_commitment_ids.filtered(lambda c: c.state != "cancel"):
            return
        if not self.budget_account_id:
            raise UserError(
                _("กรุณาระบุรหัสงบประมาณก่อนตั้งสถานะพร้อมดำเนินการ")
            )
        if self.total_price <= 0:
            raise UserError(
                _("กรุณาระบุวงเงินรวมให้มากกว่า 0 ก่อนจองงบประมาณ")
            )
        analytic_data = {
            "account_id": self.budget_account_id.id,
            "activity_analytic_id": self.activity_analytic_id.id or False,
            "department_analytic_id": self.department_analytic_id.id or False,
            "fund_analytic_id": self.fund_analytic_id.id or False,
            "source_analytic_id": self.source_analytic_id.id or False,
        }
        allow_negative = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        )
        if not allow_negative:
            self.env["budget.controller"].check_budget_availability(
                analytic_data,
                self.total_price,
                self.account_fiscal_year_id.id,
                self.company_id.id,
            )
        dist = dict(self.analytic_distribution or {})
        commitment = self.env["budget.commitment"].create(
            {
                "account_id": self.budget_account_id.id,
                "amount": self.total_price,
                "analytic_distribution": dist or False,
                "account_fiscal_year_id": self.account_fiscal_year_id.id,
                "company_id": self.company_id.id,
                "date": fields.Date.context_today(self),
                "ref": self.name,
                "description": self.description,
                "procurement_plan_id": self.id,
                "user_id": self.env.user.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "move_type": "reserve",
                            "account_id": self.budget_account_id.id,
                            "analytic_distribution": dist or False,
                            "amount": self.total_price,
                            "name": _("Initial reservation"),
                        },
                    )
                ],
            }
        )
        commitment.action_reserve()
        self.message_post(
            body=_("จองงบประมาณ %s จำนวน %s")
            % (
                commitment.name,
                format_amount(self.env, self.total_price, self.currency_id),
            )
        )

    def _release_plan_commitment(self):
        """Release the plan's reservation when it leaves the active band
        (on hold / reset to draft). Cancels the commitment only while it is still
        untouched AND usage has not started; once the plan is in progress (a
        downstream document has linked the reservation) or any obligate/consume
        draw-down exists, the commitment is kept and a note is posted so in-flight
        spending is never stranded (D3)."""
        for plan in self:
            in_use = plan.state == "in_progress"
            for commitment in plan.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            ):
                if (
                    in_use
                    or commitment.total_obligated
                    or commitment.total_consumed
                ):
                    plan.message_post(
                        body=_(
                            "งบประมาณที่จองไว้ (%s) มีการใช้งานแล้ว "
                            "จึงไม่ยกเลิกการจอง"
                        )
                        % commitment.name
                    )
                    continue
                commitment.action_cancel()
                plan.message_post(
                    body=_("ยกเลิกการจองงบประมาณ %s") % commitment.name
                )

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

    budget_commitment_ids = fields.One2many(
        "budget.commitment", "procurement_plan_id", string="ผูกพันงบประมาณ", readonly=True
    )
    budget_commitment_count = fields.Integer(
        string="จำนวนผูกพันงบประมาณ", compute="_compute_budget_commitment_count"
    )

    budget_account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        tracking=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
        states=READONLY_STATES,
    )

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

    def _compute_budget_commitment_count(self):
        for rec in self:
            rec.budget_commitment_count = len(rec.budget_commitment_ids)

    def action_view_budget_commitment(self):
        self.ensure_one()
        action = (
            self.env.ref(
                "procurement_plan_budget.action_budget_commitment_procurement_plan"
            )
            .sudo()
            .read()[0]
        )
        action["domain"] = [("procurement_plan_id", "=", self.id)]
        action["context"] = {"default_procurement_plan_id": self.id}
        return action

    def action_open_budget_commitments(self):
        self.ensure_one()
        return {
            "name": "Budget Commitments",
            "type": "ir.actions.act_window",
            "res_model": "budget.commitment",
            "view_mode": "tree,form",
            "domain": [("procurement_plan_id", "=", self.id)],
        }
