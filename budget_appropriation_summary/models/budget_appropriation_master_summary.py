import base64

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.pdf import merge_pdf


class BudgetAppropriationMasterSummary(models.Model):
    _name = "budget.appropriation.master.summary"
    _description = "Budget Appropriation Master Summary"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "done": [("readonly", True)],
    }

    PRINT_REPORT_ORDER = [
        "action_report_f2_revenue",
        "action_report_f4p_revenue",
        "action_report_f4w_revenue",
        "action_report_f3w_f6w_revenue",
        "action_report_f7w_expense",
        "action_report_f5p_expense",
        "action_report_f5w_expense",
        "action_report_f8w_expense",
        "action_report_f9w_expense",
        "action_report_f11w_expense",
        "action_report_f10w_expense",
    ]

    name = fields.Char(
        string="ชื่อสรุปภาพรวม",
        compute="_compute_name",
        store=True,
        readonly=True,
        tracking=True,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="ปีงบประมาณ",
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    source_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="แหล่งเงิน",
        domain=[("root_plan_id.code", "=", "sources")],
        required=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    compare_summary_id = fields.Many2one(
        comodel_name="budget.appropriation.master.summary",
        string="สรุปเปรียบเทียบ",
        help="สำหรับเปรียบเทียบกับสรุปภาพรวมปีก่อน",
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
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
    compilation_ids = fields.One2many(
        comodel_name="budget.appropriation.compilation",
        inverse_name="master_summary_id",
        string="รวมเล่มหน่วยงาน",
        readonly=False,
        states=READONLY_STATES,
    )
    revenue_appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        string="ประมาณการรายรับทั้งหมด",
        compute="_compute_all_appropriation_ids",
        store=False,
    )
    expense_appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        string="ประมาณการรายจ่ายทั้งหมด",
        compute="_compute_all_appropriation_ids",
        store=False,
    )
    amount_revenue_total = fields.Monetary(
        string="รายรับรวมทั้งสถาบัน",
        compute="_compute_amount_totals",
        store=True,
        currency_field="currency_id",
    )
    amount_expense_total = fields.Monetary(
        string="รายจ่ายรวมทั้งสถาบัน",
        compute="_compute_amount_totals",
        store=True,
        currency_field="currency_id",
    )
    amount_revenue_gross = fields.Monetary(
        string="รายรับรวม",
        compute="_compute_revenue_breakdown",
        store=True,
        currency_field="currency_id",
    )
    amount_revenue_deduct = fields.Monetary(
        string="หักโอน",
        compute="_compute_revenue_breakdown",
        store=True,
        currency_field="currency_id",
    )
    reserve_fund_amount = fields.Monetary(
        string="งบกองทุนสำรอง",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    personnel_expense_amount = fields.Monetary(
        string="งบบุคลากร",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    operating_expense_amount = fields.Monetary(
        string="งบดำเนินงาน",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    capital_expenditure_amount = fields.Monetary(
        string="งบลงทุน",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    subsidy_amount = fields.Monetary(
        string="งบเงินอุดหนุน",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
    )
    other_expenditure_amount = fields.Monetary(
        string="งบรายจ่ายอื่น",
        compute="_compute_budget_summary_amounts",
        currency_field="currency_id",
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
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Created by",
        default=lambda self: self.env.user,
        readonly=True,
    )
    note = fields.Text(
        string="หมายเหตุ",
        readonly=False,
    )
    final_document = fields.Binary(
        string="ไฟล์ฉบับสมบูรณ์",
        attachment=True,
        help="ไฟล์งบประมาณสถาบันฉบับสมบูรณ์ที่ export ออกไปจัดรูปแบบ/แทรกหน้า/"
        "ใส่ references นอกระบบแล้วนำกลับมาอัปโหลดเข้าระบบ",
    )
    final_document_filename = fields.Char(
        string="ชื่อไฟล์ฉบับสมบูรณ์",
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
    f7w_expense_data = fields.Json(
        string="F7-W Expense Data",
        compute="_compute_f7w_expense_data",
        store=False,
    )
    f8w_expense_data = fields.Json(
        string="F8-W Expense Data",
        compute="_compute_f8w_expense_data",
        store=False,
    )
    f9w_expense_data = fields.Json(
        string="F9-W Expense Data",
        compute="_compute_f9w_expense_data",
        store=False,
    )
    f10w_expense_data = fields.Json(
        string="F10-W Expense Data",
        compute="_compute_f10w_expense_data",
        store=False,
    )
    f11w_expense_data = fields.Json(
        string="F11-W Expense Data",
        compute="_compute_f11w_expense_data",
        store=False,
    )

    @api.depends("source_analytic_id", "account_fiscal_year_id")
    def _compute_name(self):
        for record in self:
            record.name = _("สรุปภาพรวม (%s) ปีงบประมาณ พ.ศ. %s") % (
                record.source_analytic_id.name or "",
                record.account_fiscal_year_id.name or "",
            )

    @api.constrains("compare_summary_id")
    def _check_compare_summary_id(self):
        for record in self:
            if record.compare_summary_id and record.compare_summary_id.id == record.id:
                raise ValidationError(
                    _("ไม่สามารถเลือกสรุปภาพรวมตัวเองเป็นรายงานเปรียบเทียบได้")
                )

    @api.depends(
        "compilation_ids.revenue_appropriation_ids",
        "compilation_ids.expense_appropriation_ids",
    )
    def _compute_all_appropriation_ids(self):
        for record in self:
            revenue = self.env["budget.appropriation"]
            expense = self.env["budget.appropriation"]
            for compilation in record.compilation_ids:
                revenue |= compilation.revenue_appropriation_ids
                expense |= compilation.expense_appropriation_ids
            record.revenue_appropriation_ids = revenue
            record.expense_appropriation_ids = expense

    @api.depends(
        "compilation_ids.amount_revenue_total",
        "compilation_ids.amount_expense_total",
    )
    def _compute_amount_totals(self):
        for record in self:
            record.amount_revenue_total = sum(
                record.compilation_ids.mapped("amount_revenue_total")
            )
            record.amount_expense_total = sum(
                record.compilation_ids.mapped("amount_expense_total")
            )

    @api.depends(
        "compilation_ids.revenue_appropriation_ids.amount_total",
        "compilation_ids.revenue_appropriation_ids.amount_deduct",
    )
    def _compute_revenue_breakdown(self):
        for record in self:
            record.amount_revenue_gross = sum(
                record.revenue_appropriation_ids.mapped("amount_total")
            )
            record.amount_revenue_deduct = sum(
                record.revenue_appropriation_ids.mapped("amount_deduct")
            )

    BUDGET_SUMMARY_FIELDS = [
        "reserve_fund_amount",
        "personnel_expense_amount",
        "operating_expense_amount",
        "capital_expenditure_amount",
        "subsidy_amount",
        "other_expenditure_amount",
    ]

    @api.depends(
        "compilation_ids.reserve_fund_amount",
        "compilation_ids.personnel_expense_amount",
        "compilation_ids.operating_expense_amount",
        "compilation_ids.capital_expenditure_amount",
        "compilation_ids.subsidy_amount",
        "compilation_ids.other_expenditure_amount",
    )
    def _compute_budget_summary_amounts(self):
        for record in self:
            for field_name in self.BUDGET_SUMMARY_FIELDS:
                record[field_name] = sum(
                    record.compilation_ids.mapped(field_name)
                )

    @api.depends("revenue_appropriation_ids", "compare_summary_id")
    def _compute_f2_revenue_data(self):
        F2Model = self.env["budget.appropriation.summary.f2.revenue"]
        for record in self:
            record.f2_revenue_data = F2Model.get_data(record.id)

    @api.depends("revenue_appropriation_ids", "compare_summary_id")
    def _compute_f4p_revenue_data(self):
        Model = self.env["budget.appropriation.summary.f4p.revenue"]
        for record in self:
            record.f4p_revenue_data = Model.get_data(record.id)

    @api.depends("revenue_appropriation_ids", "compare_summary_id")
    def _compute_f4w_revenue_data(self):
        Model = self.env["budget.appropriation.summary.f4w.revenue"]
        for record in self:
            record.f4w_revenue_data = Model.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_summary_id")
    def _compute_f5p_expense_data(self):
        Model = self.env["budget.appropriation.summary.f5p.expense"]
        for record in self:
            record.f5p_expense_data = Model.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_summary_id")
    def _compute_f5w_expense_data(self):
        Model = self.env["budget.appropriation.summary.f5w.expense"]
        for record in self:
            record.f5w_expense_data = Model.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_summary_id")
    def _compute_f7w_expense_data(self):
        Model = self.env["budget.appropriation.summary.f7w.expense"]
        for record in self:
            record.f7w_expense_data = Model.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_summary_id")
    def _compute_f8w_expense_data(self):
        Model = self.env["budget.appropriation.summary.f8w.expense"]
        for record in self:
            record.f8w_expense_data = Model.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_summary_id")
    def _compute_f9w_expense_data(self):
        Model = self.env["budget.appropriation.summary.f9w.expense"]
        for record in self:
            record.f9w_expense_data = Model.get_data(record.id)

    @api.depends("expense_appropriation_ids")
    def _compute_f10w_expense_data(self):
        Model = self.env["budget.appropriation.summary.f10w.expense"]
        for record in self:
            record.f10w_expense_data = Model.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_summary_id")
    def _compute_f11w_expense_data(self):
        Model = self.env["budget.appropriation.summary.f11w.expense"]
        for record in self:
            record.f11w_expense_data = Model.get_data(record.id)

    def action_confirm(self):
        for record in self:
            not_confirmed = record.compilation_ids.filtered(
                lambda c: c.state not in ("confirmed", "done")
            )
            if not_confirmed:
                names = ", ".join(not_confirmed.mapped("name"))
                raise ValidationError(
                    _(
                        "ไม่สามารถยืนยันสรุปภาพรวมได้ เนื่องจากรวมเล่มหน่วยงานต่อไปนี้ยังไม่ได้รับการยืนยัน:\n%s"
                    )
                    % names
                )
        self.write({"state": "confirmed"})

    def action_done(self):
        self.ensure_one()
        wizard = self.env["budget.appropriation.master.summary.done.wizard"].create(
            {"master_summary_id": self.id}
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "budget.appropriation.master.summary.done.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open_report(self):
        """Open the combined report in a new browser tab as HTML."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_summary/{self.id}/html",
            "target": "new",
        }

    def _get_merged_pdf(self):
        """Render each sub-report with its own paperformat and merge into one PDF.

        Using merge_pdf preserves each report's orientation (portrait/landscape)
        and starts every sub-report on a new page.
        """
        self.ensure_one()
        pdfs = []
        for ref in self.PRINT_REPORT_ORDER:
            report = self.env.ref(f"budget_appropriation_summary.{ref}")
            pdf_content, __ = report._render_qweb_pdf(report.id, self.ids)
            pdfs.append(pdf_content)
        return merge_pdf(pdfs)

    def _get_pdf_filename(self):
        """Return an ASCII-safe PDF filename so it survives HTTP transport."""
        self.ensure_one()
        parts = [
            self.source_analytic_id.code or "",
            self.account_fiscal_year_id.name or "",
        ]
        slug = "-".join(p for p in parts if p) or str(self.id)
        return f"budget-summary-{slug}.pdf"

    def action_print_report(self):
        self.ensure_one()
        merged = self._get_merged_pdf()
        attachment = self.env["ir.attachment"].create(
            {
                "name": self._get_pdf_filename(),
                "type": "binary",
                "datas": base64.b64encode(merged),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/pdf",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=false",
            "target": "new",
        }

    # --- Individual report actions ---

    REPORT_MAP = {
        "f2": "action_report_f2_revenue",
        "f4p": "action_report_f4p_revenue",
        "f4w": "action_report_f4w_revenue",
        "f3w_f6w": "action_report_f3w_f6w_revenue",
        "f5p": "action_report_f5p_expense",
        "f5w": "action_report_f5w_expense",
        "f7w": "action_report_f7w_expense",
        "f8w": "action_report_f8w_expense",
        "f9w": "action_report_f9w_expense",
        "f10w": "action_report_f10w_expense",
        "f11w": "action_report_f11w_expense",
    }

    def _action_open_individual_report(self, report_name):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/budget_appropriation_summary/{self.id}"
                f"/report/{report_name}/html"
            ),
            "target": "new",
        }

    def action_open_f2_report(self):
        return self._action_open_individual_report("f2")

    def action_open_f4p_report(self):
        return self._action_open_individual_report("f4p")

    def action_open_f4w_report(self):
        return self._action_open_individual_report("f4w")

    def action_open_f3w_f6w_report(self):
        return self._action_open_individual_report("f3w_f6w")

    def action_open_f5p_report(self):
        return self._action_open_individual_report("f5p")

    def action_open_f5w_report(self):
        return self._action_open_individual_report("f5w")

    def action_open_f7w_report(self):
        return self._action_open_individual_report("f7w")

    def action_open_f8w_report(self):
        return self._action_open_individual_report("f8w")

    def action_open_f9w_report(self):
        return self._action_open_individual_report("f9w")

    def action_open_f10w_report(self):
        return self._action_open_individual_report("f10w")

    def action_open_f11w_report(self):
        return self._action_open_individual_report("f11w")
