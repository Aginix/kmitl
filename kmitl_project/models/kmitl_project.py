# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class KmitlProject(models.Model):
    _name = "kmitl.project"
    _description = "KMITL Project"
    _order = "id desc"
    _rec_names_search = ["name", "key"]
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin", "portal.mixin"]

    READONLY_STATES = {
        "draft": [("readonly", False)],
        "new": [("readonly", True)],
        "in_progress": [("readonly", True)],
        "on_hold": [("readonly", True)],
        "complete": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        "Name",
        tracking=True,
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    project_type = fields.Selection(
        [("project", "Project/Activity"), ("strategic_project", "Strategic Project")],
        required=True,
        default="project",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    introduction = fields.Text(
        string="หลักการและเหตุผล",
        tracking=True,
        readonly=False,
        states={"complete": [("readonly", True)]},
    )
    objective = fields.Text(
        string="วัตถุประสงค์",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    national_strategy_id = fields.Many2one(
        "project.strategic.plan",
        string="ยุทธศาสตร์ชาติ",
        domain="[('level', '=', 1)]",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    master_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนแม่บทภายใต้ยุทธศาสตร์ชาติ",
        domain="[('level', '=', 2)]",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    nesdc_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนพัฒนาเศรษฐกิจและสังคมแห่งชาติ ฉบับที่ 13",
        domain=lambda self: [("id", "child_of", self.env.ref("kmitl_project.P13").id)],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    kmitl_plan_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนกลยุทธสถาบัน",
        domain="[('level', '=', 3)]",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    location = fields.Text(string="สถานที่/พื้นที่ดำเนินโครงการ", copy=True, tracking=True)
    key = fields.Char(tracking=True, readonly=True)
    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal year",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    manager_id = fields.Many2one(
        "hr.employee",
        string="หัวหน้าโครงการ",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="พนักงานผู้เป็นหัวหน้า/ผู้จัดการโครงการ; สิทธิ์เข้าถึงของผู้ใช้ผูกผ่าน manager_id.user_id",
    )
    creating_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        readonly=True,
    )
    date_start = fields.Date(
        string="Start Date",
        required=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    date_end = fields.Date(
        string="End Date",
        required=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("new", "Not started yet"),
            ("in_progress", "In Progress"),
            ("on_hold", "On Hold"),
            ("complete", "Completed"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        index=True,
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
    )

    impact_id = fields.Many2one(
        comodel_name="project.impact",
        string="Impact",
        copy=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    global_index_id = fields.Many2one(
        comodel_name="project.global.index",
        string="Global Index",
        copy=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    fight_id = fields.Many2one(
        comodel_name="project.fight",
        string="ความสอดคล้องกับค่านิยม : FIGHT",
        copy=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    methodology_ids = fields.Many2many(
        comodel_name="project.methodology",
        string="วิธีดำเนินการ",
        copy=True,
        tracking=True,
        readonly=False,
        states={"complete": [("readonly", True)]},
    )

    methodology_detail = fields.Text(
        "วิธีดำเนินการ (รายละเอียด)",
        copy=True,
        tracking=True,
        readonly=False,
        states={"complete": [("readonly", True)]},
    )

    target_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "target")],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    participant_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "participant")],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    organizer_ids = fields.One2many(
        "project.target",
        "project_id",
        string="กลุ่มเป้าหมาย/ผู้ดำเนินโครงการ",
        domain=[("line_type", "=", "organizer")],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    output_ids = fields.One2many(
        "project.output",
        "project_id",
        string="ผลผลิต",
        domain=[("line_type", "=", "output")],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    outcome_ids = fields.One2many(
        "project.output",
        "project_id",
        string="ผลลัพธ์",
        domain=[("line_type", "=", "outcome")],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    plan_ids = fields.One2many(
        "project.plan",
        "project_id",
        string="แผนการดำเนินงานและแผนการใช้จ่ายงบประมาณ",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    expected_outcome_ids = fields.One2many(
        "project.expected.outcome",
        "project_id",
        string="ผลที่คาดว่าจะได้รับ",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    evaluation_ids = fields.Many2many(
        comodel_name="project.evaluation",
        string="วิธีการ/เครื่องมือติดตามและประเมินผล",
        copy=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    evaluation_detail = fields.Text(
        "วิธีการ/เครื่องมือติดตามและประเมินผล (รายละเอียด)",
        copy=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
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

    active = fields.Boolean(default=True)
    is_editable = fields.Boolean(compute="_compute_is_editable")

    budget_account_id = fields.Many2one(comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=True,
        index=True,
        tracking=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense'),"
        " ('is_project', '=', True), ('project_type', '=', project_type)]",
        states=READONLY_STATES
    )

    budget_amount = fields.Float(
        string="งบประมาณ",
        digits="Product Price",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="งบประมาณที่ได้รับจัดสรร",
    )

    budget_commitment_ids = fields.One2many(
        "budget.commitment",
        "kmitl_project_id",
        string="ผูกพันงบประมาณ",
        readonly=True,
    )
    budget_commitment_count = fields.Integer(
        string="จำนวนผูกพันงบประมาณ",
        compute="_compute_budget_commitment_count",
    )
    budget_remaining = fields.Float(
        string="งบประมาณคงเหลือ",
        compute="_compute_budget_remaining",
        help="งบประมาณที่จองไว้ของโครงการ หักด้วยยอดที่เบิกจ่าย (ใช้) ไปแล้ว",
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_id",
        inverse="_inverse_activity_analytic",
        domain=[("root_plan_id.code", "=", "activities")],
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse="_inverse_department_analytic",
        domain=[("root_plan_id.code", "=", "departments")],
        store=False,
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
        store=False,
        tracking=True,
        states=READONLY_STATES,
    )

    _analytic_keys = {
        "activities": "activity_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "sources": "source_analytic_id",
        "kmitl_project": "analytic_account_id",
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
            line._update_analytic_distribution("kmitl_project")

    @api.onchange("operating_unit_id")
    def _onchange_operating_unit_id(self):
        """Clear department if it doesn't belong to the selected operating unit"""
        if self.department_id and self.department_id.operating_unit_id:
            if self.department_id.operating_unit_id != self.operating_unit_id:
                self.department_id = False

    def button_cancel(self):
        self._release_project_commitment()
        self.write({"state": "cancel"})

    def button_draft(self):
        self._release_project_commitment()
        self.write({"state": "draft"})

    def button_new(self):
        for project in self:
            project._reserve_project_commitment()
        self.write({"state": "new"})

    def button_in_progress(self):
        self.write({"state": "in_progress"})

    def button_on_hold(self):
        self._release_project_commitment()
        self.write({"state": "on_hold"})

    def button_complete(self):
        self.write({"state": "complete"})

    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ('draft', 'cancel'):
                rec.is_editable = True
            else:
                rec.is_editable = False

    def unlink(self):
        for rec in self:
            if rec.state != "cancel":
                raise UserError(
                    _("You cannot delete a record. Please cancel the record first.")
                )
        return super().unlink()

    def action_preview_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/my/kmitl-project/%s' % self.id
        }

    def _compute_budget_commitment_count(self):
        for rec in self:
            rec.budget_commitment_count = len(rec.budget_commitment_ids)

    @api.depends(
        "budget_amount",
        "budget_commitment_ids.state",
        "budget_commitment_ids.total_consumed",
    )
    def _compute_budget_remaining(self):
        """Money left in the project = reserved budget − what has actually been
        consumed (เบิกจ่าย) from its commitment. Not the budget-account dashboard
        status — strictly this project's reservation vs its spend."""
        for rec in self:
            used = sum(
                rec.budget_commitment_ids.filtered(
                    lambda c: c.state != "cancel"
                ).mapped("total_consumed")
            )
            rec.budget_remaining = rec.budget_amount - used

    def action_open_budget_commitments(self):
        self.ensure_one()
        return {
            "name": _("ผูกพันงบประมาณ"),
            "type": "ir.actions.act_window",
            "res_model": "budget.commitment",
            "view_mode": "tree,form",
            "domain": [("kmitl_project_id", "=", self.id)],
        }

    @api.model
    def _create_analytic_account_from_values(self, values):
        return self.env["account.analytic.account"].create(
            {
                "name": values.get("name", _("Unknown Analytic Account")),
                "code": values.get("code"),
                "company_id": self.env.company.id,
                "plan_id": self.env.ref(
                    "kmitl_project.analytic_plan_project",
                    raise_if_not_found=True,
                ).id,
            }
        )

    def _ensure_analytic_account(self):
        """A confirmed project tracks its own ``kmitl_project`` analytic dimension so
        its reservation and downstream spend are attributable to the project. Create
        it on demand (kmitl.project, unlike procurement.plan, has no auto-create on
        write) and let the inverse fold it into ``analytic_distribution``."""
        self.ensure_one()
        if self.analytic_account_id:
            return
        self.analytic_account_id = self._create_analytic_account_from_values(
            {"name": self.name, "code": self.key or self.name}
        ).id

    def _reserve_project_commitment(self):
        """Reserve one shared budget.commitment for the project's full
        ``budget_amount`` when it is confirmed (``draft``->``new``), drawing from the
        floating project-code pool (ADR-0007). Idempotent: skips when an active
        (non-cancelled) commitment already exists. Blocks on insufficient budget
        unless ``budget.allow_negative`` is set. The project's purchase requests and
        disbursements draw this single commitment down."""
        self.ensure_one()
        if self.budget_commitment_ids.filtered(lambda c: c.state != "cancel"):
            return
        if not self.budget_account_id:
            raise UserError(_("กรุณาระบุรหัสงบประมาณก่อนจองงบประมาณ"))
        if self.budget_amount <= 0:
            raise UserError(_("กรุณาระบุงบประมาณให้มากกว่า 0 ก่อนจองงบประมาณ"))
        self._ensure_analytic_account()
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
                self.budget_amount,
                self.account_fiscal_year_id.id,
                self.company_id.id,
            )
        dist = dict(self.analytic_distribution or {})
        commitment = self.env["budget.commitment"].create(
            {
                "account_id": self.budget_account_id.id,
                "amount": self.budget_amount,
                "analytic_distribution": dist or False,
                "account_fiscal_year_id": self.account_fiscal_year_id.id,
                "company_id": self.company_id.id,
                "date": fields.Date.context_today(self),
                "ref": self.key or self.name,
                "description": self.name,
                "kmitl_project_id": self.id,
                "user_id": self.env.user.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "move_type": "reserve",
                            "account_id": self.budget_account_id.id,
                            "analytic_distribution": dist or False,
                            "amount": self.budget_amount,
                            "name": _("Initial reservation"),
                        },
                    )
                ],
            }
        )
        commitment.action_reserve()
        self.message_post(
            body=_("จองงบประมาณ %s จำนวน %s บาท")
            % (commitment.name, "{:,.2f}".format(self.budget_amount))
        )

    def _release_project_commitment(self):
        """Release the reservation when the project leaves the active band
        (on hold / cancel / reset to draft). Cancels the commitment only while it is
        untouched and no draw-down has started; once the project is in progress or
        any obligate/consume exists, the commitment is kept and a note is posted so
        in-flight spending is never stranded (ADR-0007)."""
        for project in self:
            in_use = project.state == "in_progress"
            for commitment in project.budget_commitment_ids.filtered(
                lambda c: c.state in ("reserved", "partial")
            ):
                if in_use or commitment.total_obligated or commitment.total_consumed:
                    project.message_post(
                        body=_(
                            "งบประมาณที่จองไว้ (%s) มีการใช้งานแล้ว จึงไม่ยกเลิกการจอง"
                        )
                        % commitment.name
                    )
                    continue
                commitment.action_cancel()
                project.message_post(
                    body=_("ยกเลิกการจองงบประมาณ %s") % commitment.name
                )
