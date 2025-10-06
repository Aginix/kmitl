import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    """
    Budget Appropriation Line - Individual line items within budget appropriations.

    Business Purpose:
        Represents individual budget allocation items within appropriations,
        providing detailed breakdown without the complexity of double-entry
        accounting. These lines are used for planning and approval before
        creating actual budget moves.

    Key Features:
        • Simple balance tracking without debit/credit
        • Complete 4D analytic distribution
        • Integration with budget accounts
        • Converts to budget.move.line when posted

    Analytic Distribution:
        Each line maintains complete 4D analytic breakdown:
        • Budget Account: Specific chart of accounts item
        • Activity: งานบริหาร > งานสำนักงาน > งานธุรการ
        • Department: สำนักงานอธิการบดี > งานบุคคล
        • Fund: เงินรายได้ > เงินค่าบำรุง
        • Source: เงินแผ่นดิน, เงินนอกงบประมาณ
    """

    _name = "budget.appropriation.line"
    _description = "Budget Appropriation Line"
    _inherit = ["analytic.distribution.mixin", "mail.thread"]
    _order = "date desc, appropriation_name desc, id"

    appropriation_id = fields.Many2one(
        comodel_name="budget.appropriation",
        string="รายการจัดสรร",
        copy=True,
        required=True,
        readonly=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )
    appropriation_name = fields.Char(
        string="Number",
        related="appropriation_id.name",
        store=True,
        index="btree",
    )
    date = fields.Date(related="appropriation_id.date", store=True)
    code = fields.Char(related="account_id.code", store=True, tracking=True)
    name = fields.Char("ชื่อรายการ", related="account_id.name", store=True, tracking=True)
    description = fields.Char("รายละเอียด", tracking=True)
    deduct = fields.Boolean(related="account_id.deduct", store=True)
    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        index=True,
        required=True,
        domain="[('budget_type', '=', budget_type), ('deduct', '=', deduct)]",
        tracking=True,
        auto_join=True,
    )
    budget_type = fields.Selection(
        related="appropriation_id.journal_id.default_budget_type",
        store=True,
        readonly=True,
    )
    balance = fields.Float(
        string="จำนวนเงิน",
        digits="Budget Precision",
        help="Appropriation Amount",
        readonly=False,
        tracking=True,
    )
    note = fields.Text(
        "หมายเหตุ",
        help="Additional notes for this appropriation line",
        tracking=True,
    )
    company_id = fields.Many2one(
        related="appropriation_id.company_id",
        store=True,
        index=True,
    )
    currency_id = fields.Many2one(
        related="appropriation_id.currency_id",
        store=True,
    )
    parent_state = fields.Selection(
        related="appropriation_id.state",
        store=True,
    )
    date_range_fy_id = fields.Many2one(
        related="appropriation_id.date_range_fy_id",
        store=True,
    )
    journal_id = fields.Many2one(
        related="appropriation_id.journal_id",
        store=True,
    )

    deduct_analytic_id = fields.Many2one(
        "account.analytic.account",
        compute="_compute_account_id",
        string="หักให้หน่วยงาน",
        domain=[("root_plan_id.code", "=", "departments")],
        store=True,
        readonly=False,
    )
    # Analytic fields for easier access
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        related="appropriation_id.department_analytic_id",
        store=True,
        readonly=True,
        auto_join=True,
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        domain=[("root_plan_id.code", "=", "activities")],
        tracking=True,
        auto_join=True,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        domain=[("root_plan_id.code", "=", "funds")],
        tracking=True,
        auto_join=True,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        related="appropriation_id.source_analytic_id",
        store=True,
        readonly=True,
        auto_join=True,
    )

    @api.depends("account_id")
    def _compute_account_id(self):
        for rec in self:
            if rec.account_id.deduct and rec.account_id.default_deduct_analytic_id:
                rec.deduct_analytic_id = rec.account_id.default_deduct_analytic_id.id

    @api.onchange("balance")
    def _onchange_balance(self):
        """Update total when balance changes"""
        if self.appropriation_id:
            self.appropriation_id._compute_amount()

    def unlink(self):
        """Update totals when lines are deleted"""
        appropriations = self.mapped("appropriation_id")
        result = super().unlink()
        for appropriation in appropriations:
            appropriation._compute_amount()
        return result

    def budget_move_line_vals(self):
        return {
            "account_id": self.account_id.id,
            "balance": -self.balance if self.deduct else self.balance,
            "note": self.note,
            "analytic_distribution": self.analytic_distribution,
            "activity_analytic_id": self.activity_analytic_id.id,
            "fund_analytic_id": self.fund_analytic_id.id,
            "department_analytic_id": self.department_analytic_id.id,
            "source_analytic_id": self.source_analytic_id.id,
        }
