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
        string="Budget Appropriation",
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
    code = fields.Char(
        "รหัสงบประมาณ", related="account_id.code", store=True, tracking=True
    )
    name = fields.Char("ชื่อรายการ", related="account_id.name", store=True, tracking=True)
    account_id = fields.Many2one(
        comodel_name="budget.account",
        index=True,
        required=True,
        domain="[('budget_type', '=', budget_type)]",
        tracking=True,
    )
    budget_type = fields.Selection(
        related="appropriation_id.journal_id.default_budget_type", 
        store=True, 
        readonly=True
    )
    balance = fields.Float(
        digits="Budget Precision",
        help="Appropriation Amount",
        readonly=False,
        tracking=True,
    )
    note = fields.Char(
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

    # Analytic fields for easier access
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        related="appropriation_id.department_analytic_id",
        store=True,
        readonly=True,
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กิจกรรม",
        compute="_compute_analytic_fields",
        store=True,
        tracking=True,
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_fields",
        store=True,
        tracking=True,
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        related="appropriation_id.source_analytic_id",
        store=True,
        readonly=True,
    )

    @api.depends("analytic_distribution")
    def _compute_analytic_fields(self):
        """Extract analytic dimensions from distribution JSON"""
        for line in self:
            # Reset computed fields only (department and source are related fields)
            line.activity_analytic_id = False
            line.fund_analytic_id = False

            if not line.analytic_distribution:
                continue

            # Parse analytic distribution
            for account_id_str, percentage in line.analytic_distribution.items():
                account_id = int(account_id_str)
                account = self.env["account.analytic.account"].browse(account_id)
                
                if account.root_plan_id.code == "activities":
                    line.activity_analytic_id = account.id
                elif account.root_plan_id.code == "funds":
                    line.fund_analytic_id = account.id

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