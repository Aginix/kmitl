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

    use_f23 = fields.Boolean(
        string="ใช้รายงาน F23",
        help="ถ้าเลือก จะแสดงแบบฟอร์มรายงาน F23 ให้ผู้ใช้กรอกข้อมูลเพิ่มเติม",
        states=READONLY_STATES,
        readonly=False,
    )

    treasury_replenishment_amount = fields.Monetary(
        string="ชดใช้เงินคงคลัง",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    deducted_reserve_amount = fields.Monetary(
        string="หักเงินสำรอง",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    maintenance_amount = fields.Monetary(
        string="ค่าดูแลและบำรุงรักษา",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    capital_budget_amount = fields.Monetary(
        string="งบลงทุน",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    recurrent_budget_amount = fields.Monetary(
        string="งบประจำ",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    external_funding_amount = fields.Monetary(
        string="เงินสนับสนุนจากหน่วยงานภายนอก",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    revenue_net = fields.Monetary(
        string="รายรับรวมหลังหักโอน",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    fixed_expense_total = fields.Monetary(
        string="รายจ่ายคงที่",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    fixed_expense_percentage = fields.Monetary(
        string="รายจ่ายคงที่ (ร้อยละ)",
        currency_field="currency_id",
        readonly=True,
        compute="_compute_totals",
    )

    @api.depends(
        "revenue_appropriation_ids.treasury_replenishment_amount",
        "revenue_appropriation_ids.deducted_reserve_amount",
        "revenue_appropriation_ids.maintenance_amount",
        "revenue_appropriation_ids.capital_budget_amount",
        "revenue_appropriation_ids.recurrent_budget_amount",
        "revenue_appropriation_ids.external_funding_amount",
        "revenue_appropriation_ids.revenue_net",
    )
    def _compute_totals(self):
        for record in self:
            record.treasury_replenishment_amount = sum(
                record.expense_appropriation_ids.mapped("treasury_replenishment_amount")
            )
            record.deducted_reserve_amount = sum(
                record.expense_appropriation_ids.mapped("deducted_reserve_amount")
            )
            record.maintenance_amount = sum(
                record.expense_appropriation_ids.mapped("maintenance_amount")
            )
            record.capital_budget_amount = sum(
                record.expense_appropriation_ids.mapped("capital_budget_amount")
            )
            record.recurrent_budget_amount = sum(
                record.expense_appropriation_ids.mapped("recurrent_budget_amount")
            )
            record.external_funding_amount = sum(
                record.expense_appropriation_ids.mapped("external_funding_amount")
            )
            record.revenue_net = sum(
                record.revenue_appropriation_ids.mapped("amount_net")
            )
            record.fixed_expense_total = record.revenue_net - (
                record.treasury_replenishment_amount
                + record.deducted_reserve_amount
                + record.maintenance_amount
                + record.capital_budget_amount
                + record.recurrent_budget_amount
                + record.external_funding_amount
            )
            record.fixed_expense_percentage = (record.fixed_expense_total * 100) / record.revenue_net

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
            if not record.revenue_appropriation_ids:
                record.f4_revenue_data = {}
                continue
            apps = record.revenue_appropriation_ids
            if len(apps) == 1:
                record.f4_revenue_data = {"details": [F4Model.get_f4_data(apps.id)]}
            else:
                dept_name = (record.department_analytic_id.complete_name or "").replace(
                    " / ", " "
                )
                overview = F4Model.get_f4_data(
                    apps.ids,
                    {"department_name": f"{dept_name} (ภาพรวม)"},
                )
                details = []
                for app in apps.sorted(lambda a: a.department_analytic_id.code or ""):
                    details.append(F4Model.get_f4_data(app.id))
                record.f4_revenue_data = {"overview": overview, "details": details}

    @api.depends("expense_appropriation_ids")
    def _compute_f5_expense_data(self):
        F5Model = self.env["budget.appropriation.f5.report"]
        for record in self:
            if not record.expense_appropriation_ids:
                record.f5_expense_data = {}
                continue
            apps = record.expense_appropriation_ids
            if len(apps) == 1:
                record.f5_expense_data = {"details": [F5Model.get_f5_data(apps.id)]}
            else:
                dept_name = (record.department_analytic_id.complete_name or "").replace(
                    " / ", " "
                )
                overview = F5Model.get_f5_data(
                    apps.ids,
                    {"department_name": f"{dept_name} (ภาพรวม)"},
                )
                details = []
                for app in apps.sorted(lambda a: a.department_analytic_id.code or ""):
                    details.append(F5Model.get_f5_data(app.id))
                record.f5_expense_data = {"overview": overview, "details": details}

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

    def action_open_f23w_report(self):
        """Open F23W report in a new browser tab as HTML."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/budget_appropriation_summary/compilation/{self.id}/f23w/html",
            "target": "new",
        }
