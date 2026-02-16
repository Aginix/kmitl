from odoo import _, api, fields, models


class BudgetAppropriationCompilation(models.Model):
    _name = "budget.appropriation.compilation"
    _description = "Budget Appropriation Compilation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "done": [("readonly", True)],
    }

    sequence = fields.Integer(string="ลำดับ", default=10)
    name = fields.Char(
        string="ชื่อรวมเล่ม",
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
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="หน่วยงาน",
        domain=[("root_plan_id.code", "=", "departments")],
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
    revenue_appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        relation="budget_appropriation_compilation_revenue_rel",
        column1="compilation_id",
        column2="appropriation_id",
        string="ประมาณการรายรับ",
        domain=[("budget_type", "=", "revenue")],
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    expense_appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        relation="budget_appropriation_compilation_expense_rel",
        column1="compilation_id",
        column2="appropriation_id",
        string="ประมาณการรายจ่าย",
        domain=[("budget_type", "=", "expense")],
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )
    appropriation_ids = fields.Many2many(
        comodel_name="budget.appropriation",
        string="รายการจัดสรรทั้งหมด",
        compute="_compute_appropriation_ids",
        store=False,
    )
    amount_revenue_total = fields.Monetary(
        string="รายรับรวม",
        compute="_compute_amount_totals",
        store=True,
        currency_field="currency_id",
    )
    amount_expense_total = fields.Monetary(
        string="รายจ่ายรวม",
        compute="_compute_amount_totals",
        store=True,
        currency_field="currency_id",
    )
    master_summary_id = fields.Many2one(
        comodel_name="budget.appropriation.master.summary",
        string="สรุปภาพรวมสถาบัน",
        readonly=False,
        states=READONLY_STATES,
        ondelete="set null",
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
    note = fields.Text(
        string="หมายเหตุ",
        readonly=False,
    )
    f4_revenue_data = fields.Json(
        string="F4 Revenue Data",
        compute="_compute_f4_revenue_data",
        store=False,
    )
    f5_expense_data = fields.Json(
        string="F5 Expense Data",
        compute="_compute_f5_expense_data",
        store=False,
    )

    @api.depends(
        "department_analytic_id",
        "source_analytic_id",
        "account_fiscal_year_id",
    )
    def _compute_name(self):
        for record in self:
            department = record.department_analytic_id.complete_name
            if department:
                department = department.replace(" / ", " ")
            record.name = _("%s (%s) ปีงบประมาณ พ.ศ. %s") % (
                department or "",
                record.source_analytic_id.name or "",
                record.account_fiscal_year_id.name or "",
            )

    @api.depends("revenue_appropriation_ids", "expense_appropriation_ids")
    def _compute_appropriation_ids(self):
        for record in self:
            record.appropriation_ids = (
                record.revenue_appropriation_ids | record.expense_appropriation_ids
            )

    @api.depends(
        "revenue_appropriation_ids.amount_net",
        "expense_appropriation_ids.amount_net",
    )
    def _compute_amount_totals(self):
        for record in self:
            record.amount_revenue_total = sum(
                record.revenue_appropriation_ids.mapped("amount_net")
            )
            record.amount_expense_total = sum(
                record.expense_appropriation_ids.mapped("amount_net")
            )

    @api.depends("revenue_appropriation_ids")
    def _compute_f4_revenue_data(self):
        F4Model = self.env["budget.appropriation.f4.report"]
        for record in self:
            if record.revenue_appropriation_ids:
                record.f4_revenue_data = F4Model.get_f4_data(
                    record.revenue_appropriation_ids.ids,
                    {
                        "department_name": record.department_analytic_id.complete_name.replace(
                            " / ", " "
                        )
                    },
                )
            else:
                record.f4_revenue_data = {}

    @api.depends("expense_appropriation_ids")
    def _compute_f5_expense_data(self):
        F5Model = self.env["budget.appropriation.f5.report"]
        for record in self:
            if record.expense_appropriation_ids:
                record.f5_expense_data = F5Model.get_f5_data(
                    record.expense_appropriation_ids.ids,
                    {
                        "department_name": record.department_analytic_id.complete_name.replace(
                            " / ", " "
                        )
                    },
                )
            else:
                record.f5_expense_data = {}

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_done(self):
        self.write({"state": "done"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_open_f4_report(self):
        """Open F4 revenue report in a new browser tab as HTML."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_summary/compilation/{self.id}/f4/html",
            "target": "new",
        }

    def action_open_f5_report(self):
        """Open F5 expense report in a new browser tab as HTML."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_summary/compilation/{self.id}/f5/html",
            "target": "new",
        }

    def action_print_f4_report(self):
        """Print F4 revenue report as PDF."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_summary.action_report_compilation_f4"
        ).report_action(self)

    def action_print_f5_report(self):
        """Print F5 expense report as PDF."""
        self.ensure_one()
        return self.env.ref(
            "budget_appropriation_summary.action_report_compilation_f5"
        ).report_action(self)
