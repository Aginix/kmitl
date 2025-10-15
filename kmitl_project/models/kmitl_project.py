# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class KmitlProject(models.Model):
    _name = "kmitl.project"
    _order = "id desc"
    _rec_names_search = ["name", "key"]
    _inherit = ["mail.thread", "mail.activity.mixin", "analytic.mixin", "portal.mixin"]

    READONLY_STATES = {
        "draft": [("readonly", False)],
        "confirmed": [("readonly", True)],
        "in_progress": [("readonly", True)],
        "postpone": [("readonly", True)],
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
    user_id = fields.Many2one(
        "res.users",
        tracking=True,
        default=lambda self: self.env.user,
        readonly=True,
        states={"draft": [("readonly", False)]},
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
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
        states=READONLY_STATES
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
        "project": "analytic_account_id",
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
            line._update_analytic_distribution("project")

    def button_cancel(self):
        self.write({"state": "cancel"})

    def button_draft(self):
        self.write({"state": "draft"})

    def button_confirm(self):
        self.write({"state": "confirmed"})

    def button_in_progress(self):
        self.write({"state": "in_progress"})

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
