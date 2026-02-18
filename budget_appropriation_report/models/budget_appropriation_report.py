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
        required=True,
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
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้สร้างรายงาน",
        default=lambda self: self.env.user,
        readonly=True,
    )
    amount_revenue_total = fields.Monetary(
        string="รายรับรวม",
        compute="_compute_amount_totals",
        currency_field="currency_id",
    )
    amount_expense_total = fields.Monetary(
        string="รายจ่ายรวม",
        compute="_compute_amount_totals",
        currency_field="currency_id",
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
    f11w_expense_data = fields.Json(
        string="F11-W Expense Data",
        compute="_compute_f11w_expense_data",
        store=False,
    )
    f10w_expense_data = fields.Json(
        string="F10-W Expense Data",
        compute="_compute_f10w_expense_data",
        store=False,
    )

    use_f23 = fields.Boolean(
        string="ใช้รายงาน F23",
        help="ถ้าเลือก จะแสดงแบบฟอร์มรายงาน F23 ให้ผู้ใช้กรอกข้อมูลเพิ่มเติม",
        states=READONLY_STATES,
        readonly=False,
    )

    parent_id = fields.Many2one(
        comodel_name="budget.appropriation.report",
        string="รายงานหลัก",
        readonly=False,
        states=READONLY_STATES,
    )

    child_ids = fields.One2many(
        "budget.appropriation.report",
        "parent_id",
        string="รายงานย่อย",
        readonly=False,
        states=READONLY_STATES,
    )

    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงาน",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
        required=True,
    )

    education_percentage = fields.Float(
        string="สัดส่วนการจัดสรรเพื่อการศึกษา (%)",
        help="สัดส่วนการจัดสรรงบประมาณเพื่อการศึกษา (%)",
        default=0.0,
        readonly=True,
        compute="_compute_impact_percentages",
        store=True,
    )
    education_amount = fields.Monetary(
        string="จำนวนเงินจัดสรรเพื่อการศึกษา",
        help="จำนวนเงินจัดสรรงบประมาณเพื่อการศึกษา",
        compute="_compute_impact_amounts",
        store=True,
        currency_field="currency_id",
    )

    academic_percentage = fields.Float(
        string="สัดส่วนการจัดสรรเพื่อการวิจัย (%)",
        help="สัดส่วนการจัดสรรงบประมาณเพื่อการวิจัย (%)",
        default=0.0,
        readonly=True,
        compute="_compute_impact_percentages",
        store=True,
    )
    academic_amount = fields.Monetary(
        string="จำนวนเงินจัดสรรเพื่อการวิจัย",
        help="จำนวนเงินจัดสรรงบประมาณเพื่อการวิจัย",
        compute="_compute_impact_amounts",
        store=True,
        currency_field="currency_id",
    )

    industrial_percentage = fields.Float(
        string="สัดส่วนการจัดสรรเพื่อตอบโจทย์ภาคอุตสาหกรรม (%)",
        help="สัดส่วนการจัดสรรงบประมาณเพื่อตอบโจทย์ภาคอุตสาหกรรม (%)",
        default=0.0,
        readonly=True,
        compute="_compute_impact_percentages",
        store=True,
    )
    industrial_amount = fields.Monetary(
        string="จำนวนเงินจัดสรรเพื่อตอบโจทย์ภาคอุตสาหกรรม",
        help="จำนวนเงินจัดสรรงบประมาณเพื่อตอบโจทย์ภาคอุตสาหกรรม",
        compute="_compute_impact_amounts",
        store=True,
        currency_field="currency_id",
    )

    social_percentage = fields.Float(
        string="สัดส่วนการจัดสรรเพื่อด้านสังคม (%)",
        help="สัดส่วนการจัดสรรงบประมาณเพื่อด้านสังคม (%)",
        default=0.0,
        readonly=True,
        compute="_compute_impact_percentages",
        store=True,
    )
    social_amount = fields.Monetary(
        string="จำนวนเงินจัดสรรเพื่อด้านสังคม",
        help="จำนวนเงินจัดสรรงบประมาณเพื่อด้านสังคม",
        compute="_compute_impact_amounts",
        store=True,
        currency_field="currency_id",
    )

    impact_line_ids = fields.One2many(
        "budget.appropriation.impact.line",
        "report_id",
        string="รายการสัดส่วนผลกระทบ",
        readonly=False,
        states=READONLY_STATES,
    )
    education_impact_line_ids = fields.One2many(
        "budget.appropriation.impact.line",
        "report_id",
        string="รายการสัดส่วนผลกระทบ (การศึกษา)",
        domain=[("impact_type", "=", "education")],
        readonly=False,
        states=READONLY_STATES,
    )
    academic_impact_line_ids = fields.One2many(
        "budget.appropriation.impact.line",
        "report_id",
        string="รายการสัดส่วนผลกระทบ (การวิจัย)",
        domain=[("impact_type", "=", "academic")],
        readonly=False,
        states=READONLY_STATES,
    )
    industrial_impact_line_ids = fields.One2many(
        "budget.appropriation.impact.line",
        "report_id",
        string="รายการสัดส่วนผลกระทบ (อุตสาหกรรม)",
        domain=[("impact_type", "=", "industrial")],
        readonly=False,
        states=READONLY_STATES,
    )
    social_impact_line_ids = fields.One2many(
        "budget.appropriation.impact.line",
        "report_id",
        string="รายการสัดส่วนผลกระทบ (สังคม)",
        domain=[("impact_type", "=", "social")],
        readonly=False,
        states=READONLY_STATES,
    )

    # Helper field for wizard - captures impact_type from context
    wizard_impact_type = fields.Selection(
        selection=[
            ("education", "Education"),
            ("academic", "Academic"),
            ("industrial", "Industrial"),
            ("social", "Social"),
        ],
        compute="_compute_wizard_impact_type",
        store=False,
    )

    @api.depends_context("default_impact_type")
    def _compute_wizard_impact_type(self):
        impact_type = self.env.context.get("default_impact_type", "education")
        for record in self:
            record.wizard_impact_type = impact_type

    @api.depends("impact_line_ids", "impact_line_ids.amount", "impact_line_ids.impact_type")
    def _compute_impact_percentages(self):
        for record in self:
            record.education_percentage = 0.0
            record.academic_percentage = 0.0
            record.industrial_percentage = 0.0
            record.social_percentage = 0.0

    @api.depends("impact_line_ids", "impact_line_ids.amount", "amount_expense_total")
    def _compute_impact_amounts(self):
        for record in self:
            education_amount = sum(
                line.amount for line in record.impact_line_ids if line.impact_type == "education"
            )
            academic_amount = sum(
                line.amount for line in record.impact_line_ids if line.impact_type == "academic"
            )
            industrial_amount = sum(
                line.amount for line in record.impact_line_ids if line.impact_type == "industrial"
            )
            social_amount = sum(
                line.amount for line in record.impact_line_ids if line.impact_type == "social"
            )

            record.education_amount = education_amount
            record.academic_amount = academic_amount
            record.industrial_amount = industrial_amount
            record.social_amount = social_amount

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

    @api.depends("expense_appropriation_ids", "compare_report_id")
    def _compute_f8w_expense_data(self):
        """Compute F8-W expense data for this report with comparison."""
        F8WModel = self.env["budget.appropriation.f8w.expense"]
        for record in self:
            record.f8w_expense_data = F8WModel.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_report_id")
    def _compute_f9w_expense_data(self):
        """Compute F9-W expense data (pivot table) for this report with comparison."""
        F9WModel = self.env["budget.appropriation.f9w.expense"]
        for record in self:
            record.f9w_expense_data = F9WModel.get_data(record.id)

    @api.depends("expense_appropriation_ids", "compare_report_id")
    def _compute_f11w_expense_data(self):
        """Compute F11-W expense data (pivot by funds) for this report with comparison."""
        F11WModel = self.env["budget.appropriation.f11w.expense"]
        for record in self:
            record.f11w_expense_data = F11WModel.get_data(record.id)

    @api.depends("expense_appropriation_ids")
    def _compute_f10w_expense_data(self):
        """Compute F10-W expense data (hierarchical by activity plans and expense types)."""
        F10WModel = self.env["budget.appropriation.f10w.expense"]
        for record in self:
            record.f10w_expense_data = F10WModel.get_data(record.id)

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

    @api.depends("revenue_appropriation_ids.amount_net", "expense_appropriation_ids.amount_net")
    def _compute_amount_totals(self):
        for record in self:
            record.amount_revenue_total = sum(record.revenue_appropriation_ids.mapped("amount_net"))
            record.amount_expense_total = sum(record.expense_appropriation_ids.mapped("amount_net"))

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

    def _print_all_reports(self, show_council_header=False):
        """Internal method to print all reports combined with optional council header."""
        self.ensure_one()
        pdf_streams = []
        report_actions = [
            "budget_appropriation_report.action_report_f2_revenue",
            "budget_appropriation_report.action_report_f4p_revenue",
            "budget_appropriation_report.action_report_f4w_revenue",
            "budget_appropriation_report.action_report_f3w_f6w_revenue",
            "budget_appropriation_report.action_report_f7w_expense",
            "budget_appropriation_report.action_report_f5p_expense",
            "budget_appropriation_report.action_report_f5w_expense",
            "budget_appropriation_report.action_report_f8w_expense",
            "budget_appropriation_report.action_report_f9w_expense",
            "budget_appropriation_report.action_report_f10w_expense",
            "budget_appropriation_report.action_report_f11w_expense",
        ]

        for report_action in report_actions:
            pdf, _ = self.env['ir.actions.report'].with_context(
                show_council_header=show_council_header
            )._render_qweb_pdf(report_action, self.id)
            pdf_streams.append(pdf)

        merged_pdf = merge_pdf(pdf_streams)

        suffix = "_with_header" if show_council_header else "_without_header"
        attachment = self.env["ir.attachment"].create({
            "name": f"{self.name}{suffix}.pdf",
            "type": "binary",
            "datas": base64.b64encode(merged_pdf),
            "mimetype": "application/pdf",
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def action_print_all(self):
        """Print all reports combined - รายงานรวมทั้งหมด (ไม่มีมติ)."""
        return self._print_all_reports(show_council_header=False)

    def action_print_all_with_header(self):
        """Print all reports combined with council meeting header - พิมพ์เล่มประมาณการ (มีมติ)."""
        return self._print_all_reports(show_council_header=True)

    def action_print_all_without_header(self):
        """Print all reports combined without council meeting header - พิมพ์เล่มประมาณการ (ไม่มีมติ)."""
        return self._print_all_reports(show_council_header=False)

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

    def get_impact_line_hierarchy(self, impact_type=None, min_level=3):
        """Build flattened hierarchy list from impact_line_ids for table display.

        Args:
            impact_type: Filter by impact type (education, academic, industrial, social)
            min_level: Minimum hierarchy level to display (1-based, default=3)

        Returns:
            dict: {
                'rows': [flattened list with level info],
                'total_amount': float
            }
        """
        self.ensure_one()

        # Filter lines by impact_type if specified
        lines = self.impact_line_ids
        if impact_type:
            lines = lines.filtered(lambda l: l.impact_type == impact_type)

        if not lines:
            return {"rows": [], "total_amount": 0}

        # Collect all analytic accounts and their ancestors
        analytic_accounts = lines.mapped("analytic_account_id")
        all_account_ids = set()

        for account in analytic_accounts:
            if account.parent_path:
                parent_ids = [
                    int(pid) for pid in account.parent_path.strip("/").split("/") if pid
                ]
                all_account_ids.update(parent_ids)
            all_account_ids.add(account.id)

        # Fetch all accounts with their hierarchy info
        accounts = self.env["account.analytic.account"].browse(list(all_account_ids))

        # Calculate hierarchy level for each account (1-based)
        account_levels = {}
        for acc in accounts:
            if acc.parent_path:
                level = len([p for p in acc.parent_path.strip("/").split("/") if p])
            else:
                level = 1
            account_levels[acc.id] = level

        # Group lines by their analytic account
        lines_by_account = {}
        for line in lines:
            acc_id = line.analytic_account_id.id
            if acc_id not in lines_by_account:
                lines_by_account[acc_id] = []
            lines_by_account[acc_id].append({
                "id": line.id,
                "amount": line.amount,
            })

        # Calculate totals for each account (including children)
        account_totals = {}

        def calc_total(account):
            if account.id in account_totals:
                return account_totals[account.id]
            total = sum(l["amount"] for l in lines_by_account.get(account.id, []))
            child_accounts = [
                acc for acc in accounts
                if acc.parent_id and acc.parent_id.id == account.id
            ]
            for child in child_accounts:
                total += calc_total(child)
            account_totals[account.id] = total
            return total

        # Calculate all totals first
        for acc in accounts:
            calc_total(acc)

        # Build flattened rows (only for accounts at min_level or deeper)
        rows = []

        def flatten_node(account, display_level):
            acc_level = account_levels.get(account.id, 1)

            # Only add row if at or above min_level
            if acc_level >= min_level:
                rows.append({
                    "id": f"acc_{account.id}",
                    "type": "account",
                    "level": display_level,
                    "code": account.code or "",
                    "name": account.name,
                    "amount": account_totals.get(account.id, 0),
                })

                # Add line rows under this account
                for line in lines_by_account.get(account.id, []):
                    rows.append({
                        "id": f"line_{line['id']}",
                        "type": "line",
                        "level": display_level + 1,
                        "code": "",
                        "name": "",
                        "amount": line["amount"],
                    })

            # Process children
            child_accounts = [
                acc for acc in accounts
                if acc.parent_id and acc.parent_id.id == account.id
            ]
            child_accounts = sorted(child_accounts, key=lambda a: a.code or "")
            for child in child_accounts:
                if acc_level >= min_level:
                    flatten_node(child, display_level + 1)
                else:
                    flatten_node(child, display_level)

        # Find root accounts and flatten
        root_accounts = [
            acc for acc in accounts
            if not acc.parent_id or acc.parent_id.id not in all_account_ids
        ]
        root_accounts = sorted(root_accounts, key=lambda a: a.code or "")

        for root in root_accounts:
            flatten_node(root, 0)

        # Total is sum of accounts at min_level (display roots)
        display_root_ids = [
            acc.id for acc in accounts
            if account_levels.get(acc.id, 1) == min_level
        ]
        total_amount = sum(account_totals.get(acc_id, 0) for acc_id in display_root_ids)

        return {
            "rows": rows,
            "total_amount": total_amount,
        }

    def action_save_impact_lines(self):
        """Save impact lines and close wizard."""
        return {"type": "ir.actions.act_window_close"}
