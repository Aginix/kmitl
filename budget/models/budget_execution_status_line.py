import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetExecutionStatusLine(models.TransientModel):
    _name = "budget.execution.status.line"
    _description = "Budget Execution Status Line"
    _order = "budget_account_id, activity_analytic_id, fund_analytic_id"

    report_id = fields.Many2one(
        comodel_name="budget.execution.status.report",
        string="Report",
        required=True,
        index=True,
        ondelete="cascade",
    )

    # Budget Account and Analytics
    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        required=True,
    )

    budget_account_code = fields.Char(
        related="budget_account_id.code",
        string="Account Code",
        store=True,
    )

    budget_account_name = fields.Char(
        related="budget_account_id.name",
        string="Account Name",
        store=True,
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        domain=[("root_plan_id.code", "=", "activities")],
    )

    activity_code = fields.Char(
        related="activity_analytic_id.code",
        string="Activity Code",
        store=True,
    )

    activity_name = fields.Char(
        related="activity_analytic_id.name",
        string="Activity Name",
        store=True,
    )

    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
    )

    department_code = fields.Char(
        related="department_analytic_id.code",
        string="Department Code",
        store=True,
    )

    department_name = fields.Char(
        related="department_analytic_id.name",
        string="Department Name",
        store=True,
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        domain=[("root_plan_id.code", "=", "funds")],
    )

    fund_code = fields.Char(
        related="fund_analytic_id.code",
        string="Fund Code",
        store=True,
    )

    fund_name = fields.Char(
        related="fund_analytic_id.name",
        string="Fund Name",
        store=True,
    )

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        domain=[("root_plan_id.code", "=", "sources")],
    )

    source_code = fields.Char(
        related="source_analytic_id.code",
        string="Source Code",
        store=True,
    )

    source_name = fields.Char(
        related="source_analytic_id.name",
        string="Source Name",
        store=True,
    )

    # Budget Status Amounts (9 categories as per requirements)
    initial_appropriation = fields.Monetary(
        string="งบประมาณจัดสรรต้นปี",
        currency_field="currency_id",
        help="Initial budget appropriation excluding adjustments",
    )

    current_budget = fields.Monetary(
        string="งบประมาณ (a)",
        currency_field="currency_id",
        help="Current budget including adjustments",
    )

    total_requested = fields.Monetary(
        string="ขอใช้ทั้งหมด",
        currency_field="currency_id",
        help="Total requested amounts minus cancellations",
    )

    reserved_amount = fields.Monetary(
        string="จองเงิน (b)",
        currency_field="currency_id",
        help="Reserved but not yet obligated amounts",
    )

    obligated_amount = fields.Monetary(
        string="ผูกพัน (c)",
        currency_field="currency_id",
        help="Amounts with binding obligations (contracts, advances)",
    )

    disbursed_amount = fields.Monetary(
        string="เบิกจ่ายแล้ว (d)",
        currency_field="currency_id",
        help="Actual disbursed/paid amounts",
    )

    total_used = fields.Monetary(
        string="รวม (e)",
        currency_field="currency_id",
        help="Total used: (b) + (c) + (d)",
        compute="_compute_totals",
        store=True,
    )

    remaining_budget = fields.Monetary(
        string="งบประมาณคงเหลือ (f)",
        currency_field="currency_id",
        help="Remaining budget: (a) - (e)",
        compute="_compute_totals",
        store=True,
    )

    returned_amount = fields.Monetary(
        string="ส่งคืนเงินเหลือจ่าย",
        currency_field="currency_id",
        help="Returned unspent funds",
    )

    # Computed percentages
    utilization_percentage = fields.Float(
        string="Utilization %",
        compute="_compute_percentages",
        help="Percentage of budget utilized",
    )

    reserved_percentage = fields.Float(
        string="Reserved %",
        compute="_compute_percentages",
        help="Percentage of budget reserved",
    )

    obligated_percentage = fields.Float(
        string="Obligated %",
        compute="_compute_percentages",
        help="Percentage of budget obligated",
    )

    disbursed_percentage = fields.Float(
        string="Disbursed %",
        compute="_compute_percentages",
        help="Percentage of budget disbursed",
    )

    # Related fields
    currency_id = fields.Many2one(
        related="report_id.currency_id",
        string="Currency",
    )

    company_id = fields.Many2one(
        related="report_id.company_id",
        string="Company",
    )

    @api.depends("reserved_amount", "obligated_amount", "disbursed_amount", "current_budget")
    def _compute_totals(self):
        """Compute total used and remaining budget"""
        for line in self:
            # รวม (e) = (b) + (c) + (d)
            line.total_used = line.reserved_amount + line.obligated_amount + line.disbursed_amount

            # งบประมาณคงเหลือ (f) = (a) - (e)
            line.remaining_budget = line.current_budget - line.total_used

    @api.depends("current_budget", "reserved_amount", "obligated_amount", "disbursed_amount", "total_used")
    def _compute_percentages(self):
        """Compute utilization percentages"""
        for line in self:
            if line.current_budget != 0:
                line.utilization_percentage = (line.total_used / line.current_budget) * 100
                line.reserved_percentage = (line.reserved_amount / line.current_budget) * 100
                line.obligated_percentage = (line.obligated_amount / line.current_budget) * 100
                line.disbursed_percentage = (line.disbursed_amount / line.current_budget) * 100
            else:
                line.utilization_percentage = 0.0
                line.reserved_percentage = 0.0
                line.obligated_percentage = 0.0
                line.disbursed_percentage = 0.0

    def name_get(self):
        """Custom name display"""
        result = []
        for line in self:
            name_parts = []

            if line.budget_account_code:
                name_parts.append(f"[{line.budget_account_code}]")

            if line.budget_account_name:
                name_parts.append(line.budget_account_name)

            if line.activity_code:
                name_parts.append(f"({line.activity_code})")

            name = " ".join(name_parts) if name_parts else f"Line {line.id}"
            result.append((line.id, name))

        return result

    def action_view_budget_moves(self):
        """View budget moves for this line"""
        self.ensure_one()

        domain = [
            ('state', '=', 'posted'),
            ('date', '>=', self.report_id.date_from),
            ('date', '<=', self.report_id.date_to),
            ('line_ids.account_id', '=', self.budget_account_id.id),
        ]

        # Add analytic filters
        if self.activity_analytic_id:
            domain.append(('line_ids.activity_analytic_id', '=', self.activity_analytic_id.id))

        if self.department_analytic_id:
            domain.append(('department_analytic_id', '=', self.department_analytic_id.id))

        if self.fund_analytic_id:
            domain.append(('line_ids.fund_analytic_id', '=', self.fund_analytic_id.id))

        if self.source_analytic_id:
            domain.append(('source_analytic_id', '=', self.source_analytic_id.id))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Moves: %s') % self.budget_account_name,
            'res_model': 'budget.move',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }

    def action_view_commitments(self):
        """View budget commitments for this line"""
        self.ensure_one()

        domain = [
            ('date', '>=', self.report_id.date_from),
            ('date', '<=', self.report_id.date_to),
            ('line_ids.account_id', '=', self.budget_account_id.id),
        ]

        # Add analytic filters
        if self.activity_analytic_id:
            domain.append(('line_ids.activity_analytic_id', '=', self.activity_analytic_id.id))

        if self.department_analytic_id:
            domain.append(('department_analytic_id', '=', self.department_analytic_id.id))

        if self.fund_analytic_id:
            domain.append(('line_ids.fund_analytic_id', '=', self.fund_analytic_id.id))

        if self.source_analytic_id:
            domain.append(('source_analytic_id', '=', self.source_analytic_id.id))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Commitments: %s') % self.budget_account_name,
            'res_model': 'budget.commitment',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }

    def action_view_appropriations(self):
        """View budget appropriations for this line"""
        self.ensure_one()

        domain = [
            ('move_type', '=', 'appropriation'),
            ('state', '=', 'posted'),
            ('date', '>=', self.report_id.date_from),
            ('date', '<=', self.report_id.date_to),
            ('line_ids.account_id', '=', self.budget_account_id.id),
        ]

        # Add analytic filters
        if self.activity_analytic_id:
            domain.append(('line_ids.activity_analytic_id', '=', self.activity_analytic_id.id))

        if self.department_analytic_id:
            domain.append(('department_analytic_id', '=', self.department_analytic_id.id))

        if self.fund_analytic_id:
            domain.append(('line_ids.fund_analytic_id', '=', self.fund_analytic_id.id))

        if self.source_analytic_id:
            domain.append(('source_analytic_id', '=', self.source_analytic_id.id))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Appropriations: %s') % self.budget_account_name,
            'res_model': 'budget.move',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }

    def action_view_disbursements(self):
        """View disbursements for this line"""
        self.ensure_one()

        domain = [
            ('move_type', '=', 'entry'),
            ('state', '=', 'posted'),
            ('date', '>=', self.report_id.date_from),
            ('date', '<=', self.report_id.date_to),
            ('line_ids.account_id', '=', self.budget_account_id.id),
        ]

        # Add analytic filters similar to other actions
        if self.activity_analytic_id:
            domain.append(('line_ids.activity_analytic_id', '=', self.activity_analytic_id.id))

        if self.department_analytic_id:
            domain.append(('department_analytic_id', '=', self.department_analytic_id.id))

        if self.fund_analytic_id:
            domain.append(('line_ids.fund_analytic_id', '=', self.fund_analytic_id.id))

        if self.source_analytic_id:
            domain.append(('source_analytic_id', '=', self.source_analytic_id.id))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Disbursements: %s') % self.budget_account_name,
            'res_model': 'budget.move',
            'view_mode': 'tree,form',
            'domain': domain,
            'target': 'current',
        }

    def get_status_color(self):
        """Get color coding based on budget status"""
        self.ensure_one()

        if self.remaining_budget < 0:
            return 'text-danger'  # Over budget
        elif self.utilization_percentage > 90:
            return 'text-warning'  # High utilization
        elif self.utilization_percentage > 75:
            return 'text-info'  # Medium utilization
        else:
            return 'text-success'  # Low utilization
