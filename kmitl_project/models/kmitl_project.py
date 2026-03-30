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
    approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval Status",
        default="draft",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    approval_user_id = fields.Many2one(
        "res.users",
        string="Approved/Rejected by",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approval_date = fields.Datetime(
        string="Approval Date",
        readonly=True,
        copy=False,
        tracking=True,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        readonly=True,
        tracking=True,
    )
    show_submit_button = fields.Boolean(compute="_compute_approval_buttons")
    show_approve_button = fields.Boolean(compute="_compute_approval_buttons")
    show_reject_button = fields.Boolean(compute="_compute_approval_buttons")
    show_reset_approval_button = fields.Boolean(compute="_compute_approval_buttons")

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

    budget_amount = fields.Float(
        string="งบประมาณ",
        digits="Product Price",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="งบประมาณที่ได้รับจัดสรร",
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

    @api.onchange("department_id")
    def _onchange_department_id(self):
        """Clear user if they don't belong to the selected department"""
        if self.user_id and self.department_id:
            user_departments = self.user_id.employee_ids.mapped("department_id")
            if user_departments and self.department_id not in user_departments:
                self.user_id = False

    @api.depends("state", "approval_state")
    def _compute_approval_buttons(self):
        is_manager = self.env.user.has_group(
            "kmitl_project.group_kmitl_project_manager"
        )
        for rec in self:
            rec.show_submit_button = (
                rec.state == "draft" and rec.approval_state == "draft"
            )
            rec.show_approve_button = (
                rec.approval_state == "submitted" and is_manager
            )
            rec.show_reject_button = (
                rec.approval_state == "submitted" and is_manager
            )
            rec.show_reset_approval_button = rec.approval_state == "rejected"

    def action_submit_approval(self):
        for rec in self:
            if rec.state != "draft" or rec.approval_state != "draft":
                raise UserError(
                    _("Can only submit projects in draft approval state.")
                )
        return self.button_confirm()

    def action_approve(self):
        if not self.env.user.has_group(
            "kmitl_project.group_kmitl_project_manager"
        ):
            raise UserError(
                _("Only KMITL Project Managers can approve projects.")
            )
        self.write(
            {
                "approval_state": "approved",
                "approval_user_id": self.env.user.id,
                "approval_date": fields.Datetime.now(),
                "state": "new",
            }
        )

    def action_reject(self):
        self.ensure_one()
        if not self.env.user.has_group(
            "kmitl_project.group_kmitl_project_manager"
        ):
            raise UserError(
                _("Only KMITL Project Managers can reject projects.")
            )
        return {
            "name": _("Reject Project"),
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_reset_approval(self):
        self.write(
            {
                "approval_state": "draft",
                "rejection_reason": False,
            }
        )

    def button_cancel(self):
        self.write({"state": "cancel"})

    def button_draft(self):
        self.write(
            {
                "state": "draft",
                "approval_state": "draft",
                "approval_user_id": False,
                "approval_date": False,
                "rejection_reason": False,
            }
        )

    def button_in_progress(self):
        self.write({"state": "in_progress"})

    def button_on_hold(self):
        self.write({"state": "on_hold"})

    def button_complete(self):
        self.write({"state": "complete"})

    @api.depends("state", "approval_state")
    def _compute_is_editable(self):
        for rec in self:
            rec.is_editable = rec.state in (
                "draft",
                "cancel",
            ) and rec.approval_state in ("draft", "rejected")

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
