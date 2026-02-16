from odoo import _, api, fields, models


class BudgetAppropriationMasterSummary(models.Model):
    _name = "budget.appropriation.master.summary"
    _description = "Budget Appropriation Master Summary"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "done": [("readonly", True)],
    }

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
    compilation_ids = fields.One2many(
        comodel_name="budget.appropriation.compilation",
        inverse_name="master_summary_id",
        string="รวมเล่มหน่วยงาน",
        readonly=False,
        states=READONLY_STATES,
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

    @api.depends("source_analytic_id", "account_fiscal_year_id")
    def _compute_name(self):
        for record in self:
            record.name = _("สรุปภาพรวม (%s) ปีงบประมาณ พ.ศ. %s") % (
                record.source_analytic_id.name or "",
                record.account_fiscal_year_id.name or "",
            )

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

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_done(self):
        self.write({"state": "done"})

    def action_draft(self):
        self.write({"state": "draft"})
