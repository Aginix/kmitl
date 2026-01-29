# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.pdf import merge_pdf


class BudgetAppropriationReport(models.Model):
    """
    Budget Appropriation Report - Group appropriations for council presentation.

    Business Purpose:
        Groups budget appropriations into a report package for presenting
        to the institute council meeting for approval.
    """

    _name = "budget.appropriation.report"
    _description = "Budget Appropriation Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "done": [("readonly", True)],
    }

    name = fields.Char(
        string="ชื่อรายงาน",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    compare_report_id = fields.Many2one(
        comodel_name="budget.appropriation.report",
        string="รายงานเปรียบเทียบ",
        help="สำหรับรายงานที่ต้องเปรียบเทียบกับรายงานอื่น",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    source_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("done", "Done"),
        ],
        string="สถานะ",
        required=True,
        default="draft",
        tracking=True,
        readonly=True,
    )
    note = fields.Text(
        string="หมายเหตุ",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    revenue_appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        relation="budget_appropriation_report_revenue_rel",
        column1="report_id",
        column2="appropriation_id",
        string="รายการประมาณการรายรับ",
        domain=[("budget_type", "=", "revenue")],
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    expense_appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        relation="budget_appropriation_report_expense_rel",
        column1="report_id",
        column2="appropriation_id",
        string="รายการประมาณการรายจ่าย",
        domain=[("budget_type", "=", "expense")],
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        string="รายการจัดสรรงบประมาณทั้งหมด",
        compute="_compute_appropriation_ids",
        store=False,
    )
    council_meeting_no = fields.Char(
        string="ครั้งที่ประชุม",
        help="เช่น 9/2567",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    council_meeting_date = fields.Date(
        string="วันที่มติ",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    appropriation_count = fields.Integer(
        string="จำนวนรายการ",
        compute="_compute_appropriation_count",
    )
    f2_revenue_data = fields.Json(
        string="F2 Revenue Data",
        compute="_compute_f2_revenue_data",
        store=False,
    )
    f4p_revenue_data = fields.Json(
        string="F4-P Revenue Data",
        compute="_compute_f4p_revenue_data",
        store=False,
    )
    f4w_revenue_data = fields.Json(
        string="F4-W Revenue Data",
        compute="_compute_f4w_revenue_data",
        store=False,
    )
    f7w_expense_data = fields.Json(
        string="F7-W Expense Data",
        compute="_compute_f7w_expense_data",
        store=False,
    )
    f5p_expense_data = fields.Json(
        string="F5-P Expense Data",
        compute="_compute_f5p_expense_data",
        store=False,
    )
    f5w_expense_data = fields.Json(
        string="F5-W Expense Data",
        compute="_compute_f5w_expense_data",
        store=False,
    )

    @api.depends("revenue_appropriation_ids", "compare_report_id")
    def _compute_f2_revenue_data(self):
        """Compute F2 revenue data for this report with comparison."""
        F2Model = self.env["budget.appropriation.f2.revenue"]
        for record in self:
            record.f2_revenue_data = F2Model.get_data(record.id)

    @api.depends("revenue_appropriation_ids", "compare_report_id")
    def _compute_f4p_revenue_data(self):
        """Compute F4-P revenue data for this report with comparison."""
        F4PModel = self.env["budget.appropriation.f4p.revenue"]
        for record in self:
            record.f4p_revenue_data = F4PModel.get_data(record.id)

    @api.depends("revenue_appropriation_ids", "compare_report_id")
    def _compute_f4w_revenue_data(self):
        """Compute F4-W revenue data for this report with comparison."""
        F4WModel = self.env["budget.appropriation.f4w.revenue"]
        for record in self:
            record.f4w_revenue_data = F4WModel.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_report_id")
    def _compute_f7w_expense_data(self):
        """Compute F7-W expense data for this report with comparison."""
        F7WModel = self.env["budget.appropriation.f7w.expense"]
        for record in self:
            record.f7w_expense_data = F7WModel.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_report_id")
    def _compute_f5p_expense_data(self):
        """Compute F5-P expense data for this report with comparison."""
        F5PModel = self.env["budget.appropriation.f5p.expense"]
        for record in self:
            record.f5p_expense_data = F5PModel.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_report_id")
    def _compute_f5w_expense_data(self):
        """Compute F5-W expense data for this report with comparison."""
        F5WModel = self.env["budget.appropriation.f5w.expense"]
        for record in self:
            record.f5w_expense_data = F5WModel.get_data(record.id)

    @api.constrains("compare_report_id")
    def _check_compare_report_id(self):
        for record in self:
            if record.compare_report_id and record.compare_report_id.id == record.id:
                raise ValidationError(_("ไม่สามารถเลือกรายงานตัวเองเป็นรายงานเปรียบเทียบได้"))

    @api.depends("revenue_appropriation_ids", "expense_appropriation_ids")
    def _compute_appropriation_ids(self):
        for record in self:
            record.appropriation_ids = record.revenue_appropriation_ids | record.expense_appropriation_ids

    @api.depends("revenue_appropriation_ids", "expense_appropriation_ids")
    def _compute_appropriation_count(self):
        for record in self:
            record.appropriation_count = len(record.revenue_appropriation_ids) + len(record.expense_appropriation_ids)

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_done(self):
        self.write({"state": "done"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open_report(self):
        """Open the report in a new blank page."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_report/{self.id}/html",
            "target": "new",
        }

    def action_print_pdf(self):
        """Print the PDF report."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_report/{self.id}/pdf",
            "target": "new",
        }

    def action_print_all(self):
        """Print all reports combined - รายงานรวมทั้งหมด."""
        self.ensure_one()
        pdf_streams = []

        pdf1, _ = self.env['ir.actions.report']._render_qweb_pdf("budget_appropriation_report.action_report_f2_revenue", self.id)
        pdf_streams.append(pdf1)

        pdf2, _ = self.env['ir.actions.report']._render_qweb_pdf("budget_appropriation_report.action_report_f4p_revenue", self.id)
        pdf_streams.append(pdf2)

        pdf3, _ = self.env['ir.actions.report']._render_qweb_pdf("budget_appropriation_report.action_report_f4w_revenue", self.id)
        pdf_streams.append(pdf3)

        pdf4, _ = self.env['ir.actions.report']._render_qweb_pdf("budget_appropriation_report.action_report_f3w_f6w_revenue", self.id)
        pdf_streams.append(pdf4)

        pdf5, _ = self.env['ir.actions.report']._render_qweb_pdf("budget_appropriation_report.action_report_f7w_expense", self.id)
        pdf_streams.append(pdf5)

        pdf6, _ = self.env['ir.actions.report']._render_qweb_pdf("budget_appropriation_report.action_report_f5p_expense", self.id)
        pdf_streams.append(pdf6)

        merged_pdf = merge_pdf(pdf_streams)

        attachment = self.env["ir.attachment"].create({
            "name": f"{self.name}.pdf",
            "type": "binary",
            "datas": base64.b64encode(merged_pdf),
            "mimetype": "application/pdf",
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def action_print_f2_revenue(self):
        """Print F2 Revenue Report - สรุปเปรียบเทียบประมาณการรายรับจําแนกตามประเภท."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_report.action_report_f2_revenue"
        ).report_action(self)

    def action_print_f4p_revenue(self):
        """Print F4-P Revenue Report - สรุปประมาณการรายรับจําแนกตามหน่วยงานและประเภท."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_report.action_report_f4p_revenue"
        ).report_action(self)

    def action_print_f4w_revenue(self):
        """Print F4-W Revenue Report - สรุปเปรียบเทียบประมาณการรายรับจําแนกตามหน่วยงานและประเภท."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_report.action_report_f4w_revenue"
        ).report_action(self)

    def action_view_appropriations(self):
        """Open list of appropriations linked to this report."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("รายการจัดสรรงบประมาณ"),
            "res_model": "budget.appropriation",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.appropriation_ids.ids)],
            "context": {"default_account_fiscal_year_id": self.account_fiscal_year_id.id},
        }
