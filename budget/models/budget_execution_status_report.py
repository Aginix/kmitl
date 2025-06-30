import logging
from collections import defaultdict
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BudgetExecutionStatusReport(models.TransientModel):
    _name = "budget.execution.status.report"
    _description = "Budget Execution Status Report"

    # Filter Fields
    name = fields.Char(
        string="Report Name",
        default="Budget Execution Status Report",
        required=True,
    )

    date_from = fields.Date(
        string="Date From",
        required=True,
        default=fields.Date.today,
    )

    date_to = fields.Date(
        string="Date To",
        required=True,
        default=fields.Date.today,
    )

    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        help="Filter by fiscal year",
    )

    # Analytic Filters
    activity_analytic_ids = fields.Many2many(
        "account.analytic.account",
        "budget_execution_activity_rel",
        "report_id",
        "analytic_id",
        string="Activities",
        domain=[("root_plan_id.code", "=", "activities")],
        help="Filter by specific activities",
    )

    department_analytic_ids = fields.Many2many(
        "account.analytic.account",
        "budget_execution_department_rel",
        "report_id",
        "analytic_id",
        string="Departments",
        domain=[("root_plan_id.code", "=", "departments")],
        help="Filter by specific departments",
    )

    fund_analytic_ids = fields.Many2many(
        "account.analytic.account",
        "budget_execution_fund_rel",
        "report_id",
        "analytic_id",
        string="Funds",
        domain=[("root_plan_id.code", "=", "funds")],
        help="Filter by specific funds",
    )

    source_analytic_ids = fields.Many2many(
        "account.analytic.account",
        "budget_execution_source_rel",
        "report_id",
        "analytic_id",
        string="Sources",
        domain=[("root_plan_id.code", "=", "sources")],
        help="Filter by specific sources",
    )

    # Budget Account Filters
    budget_account_ids = fields.Many2many(
        "budget.account",
        "budget_execution_account_rel",
        "report_id",
        "account_id",
        string="Budget Accounts",
        help="Filter by specific budget accounts",
    )

    budget_type = fields.Selection(
        selection=[
            ("revenue", "Revenue"),
            ("expense", "Expense"),
        ],
        string="Budget Type",
        help="Filter by budget type",
    )

    # Report Results
    line_ids = fields.One2many(
        comodel_name="budget.execution.status.line",
        inverse_name="report_id",
        string="Report Lines",
        readonly=True,
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
    )

    # Summary Fields
    total_initial_appropriation = fields.Monetary(
        string="Total Initial Appropriation",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_current_budget = fields.Monetary(
        string="Total Current Budget",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_requested = fields.Monetary(
        string="Total Requested",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_reserved = fields.Monetary(
        string="Total Reserved",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_obligated = fields.Monetary(
        string="Total Obligated",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_disbursed = fields.Monetary(
        string="Total Disbursed",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_used = fields.Monetary(
        string="Total Used",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_remaining = fields.Monetary(
        string="Total Remaining",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_returned = fields.Monetary(
        string="Total Returned",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    @api.depends("line_ids.initial_appropriation", "line_ids.current_budget",
                 "line_ids.total_requested", "line_ids.reserved_amount",
                 "line_ids.obligated_amount", "line_ids.disbursed_amount",
                 "line_ids.total_used", "line_ids.remaining_budget",
                 "line_ids.returned_amount")
    def _compute_totals(self):
        """Compute summary totals from report lines"""
        for report in self:
            report.total_initial_appropriation = sum(report.line_ids.mapped("initial_appropriation"))
            report.total_current_budget = sum(report.line_ids.mapped("current_budget"))
            report.total_requested = sum(report.line_ids.mapped("total_requested"))
            report.total_reserved = sum(report.line_ids.mapped("reserved_amount"))
            report.total_obligated = sum(report.line_ids.mapped("obligated_amount"))
            report.total_disbursed = sum(report.line_ids.mapped("disbursed_amount"))
            report.total_used = sum(report.line_ids.mapped("total_used"))
            report.total_remaining = sum(report.line_ids.mapped("remaining_budget"))
            report.total_returned = sum(report.line_ids.mapped("returned_amount"))

    def action_generate_report(self):
        """Generate the budget execution status report"""
        self.ensure_one()

        # Clear existing lines
        self.line_ids.unlink()

        # Generate report data
        report_lines = self._generate_report_data()

        # Create report lines
        line_vals = []
        for line_data in report_lines:
            line_vals.append({
                'report_id': self.id,
                **line_data
            })

        self.env["budget.execution.status.line"].create(line_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Execution Status Report'),
            'res_model': 'budget.execution.status.report',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _generate_report_data(self):
        """Generate the complete report data"""
        # Get all data using optimized queries
        initial_appropriation = self._get_initial_appropriation()
        current_budget = self._get_current_budget()
        total_requested = self._get_total_requested()
        reserved = self._get_reserved_amount()
        obligated = self._get_obligated_amount()
        disbursed = self._get_disbursed_amount()

        # Get all unique keys (combinations of budget account + analytics)
        all_keys = set()
        all_keys.update(initial_appropriation.keys())
        all_keys.update(current_budget.keys())
        all_keys.update(total_requested.keys())
        all_keys.update(reserved.keys())
        all_keys.update(obligated.keys())
        all_keys.update(disbursed.keys())

        # Create report lines
        lines = []
        for key in all_keys:
            # Unpack key
            account_id, activity_id, dept_id, fund_id, source_id = key

            # Skip if account doesn't exist
            if not account_id:
                continue

            # Get amounts for each status
            initial = initial_appropriation.get(key, 0.0)
            current = current_budget.get(key, 0.0)
            requested = total_requested.get(key, 0.0)
            reserved_amt = reserved.get(key, 0.0)
            obligated_amt = obligated.get(key, 0.0)
            disbursed_amt = disbursed.get(key, 0.0)

            # Calculate totals
            total_used = reserved_amt + obligated_amt + disbursed_amt  # รวม (e) = (b) + (c) + (d)
            remaining = current - total_used  # งบประมาณคงเหลือ (f) = (a) - (e)

            # Calculate returned amount (ส่งคืนเงินเหลือจ่าย)
            returned = max(0, disbursed_amt - requested) if requested > 0 else 0

            lines.append({
                'budget_account_id': account_id,
                'activity_analytic_id': activity_id if activity_id else False,
                'department_analytic_id': dept_id if dept_id else False,
                'fund_analytic_id': fund_id if fund_id else False,
                'source_analytic_id': source_id if source_id else False,
                'initial_appropriation': initial,
                'current_budget': current,
                'total_requested': requested,
                'reserved_amount': reserved_amt,
                'obligated_amount': obligated_amt,
                'disbursed_amount': disbursed_amt,
                'total_used': total_used,
                'remaining_budget': remaining,
                'returned_amount': returned,
            })

        return lines

    def _get_initial_appropriation(self):
        """Get initial budget appropriations excluding adjustments"""
        domain = self._build_base_domain()
        domain.extend([
            ('move_type', '=', 'appropriation'),
            # Exclude adjustment entries - could filter by journal or date criteria
        ])

        moves = self.env['budget.move'].search(domain)
        return self._group_move_data(moves, appropriation_only=True)

    def _get_current_budget(self):
        """Get total budget including all adjustments"""
        domain = self._build_base_domain()
        moves = self.env['budget.move'].search(domain)
        return self._group_move_data(moves, net_calculation=True)

    def _get_total_requested(self):
        """Get all budget requests"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('state', 'not in', ['draft']),
        ]

        # Add analytic filters for commitments
        if self.department_analytic_ids:
            domain.append(('department_analytic_id', 'in', self.department_analytic_ids.ids))

        if self.source_analytic_ids:
            domain.append(('source_analytic_id', 'in', self.source_analytic_ids.ids))

        commitments = self.env['budget.commitment'].search(domain)

        result = defaultdict(float)
        for commitment in commitments:
            for line in commitment.line_ids:
                if not self._line_matches_filters(line):
                    continue

                key = self._get_grouping_key_commitment(line)
                if commitment.state == 'cancel':
                    result[key] -= line.amount  # Subtract cancelled amounts
                else:
                    result[key] += line.amount

        return dict(result)

    def _get_reserved_amount(self):
        """Get reserved but not yet obligated amounts"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'reserved'),
        ]

        # Add analytic filters
        if self.department_analytic_ids:
            domain.append(('department_analytic_id', 'in', self.department_analytic_ids.ids))

        if self.source_analytic_ids:
            domain.append(('source_analytic_id', 'in', self.source_analytic_ids.ids))

        commitments = self.env['budget.commitment'].search(domain)

        result = defaultdict(float)
        for commitment in commitments:
            for line in commitment.line_ids:
                if not self._line_matches_filters(line):
                    continue

                key = self._get_grouping_key_commitment(line)
                result[key] += line.remaining_amount

        return dict(result)

    def _get_obligated_amount(self):
        """Get amounts with binding obligations using 'consume' type budget moves"""
        domain = self._build_base_domain()
        domain.extend([
            ('move_type', '=', 'consume'),
        ])

        moves = self.env['budget.move'].search(domain)
        return self._group_move_data(moves, obligated_only=True)

    def _get_disbursed_amount(self):
        """Get actual disbursed/paid amounts"""
        domain = self._build_base_domain()
        domain.extend([
            ('move_type', '=', 'entry'),
            # Could add criteria to identify payment/disbursement moves
        ])

        moves = self.env['budget.move'].search(domain)
        return self._group_move_data(moves, disbursed_only=True)

    def _build_base_domain(self):
        """Build base domain for budget move queries"""
        domain = [
            ('state', '=', 'posted'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]

        if self.date_range_fy_id:
            domain.append(('date_range_fy_id', '=', self.date_range_fy_id.id))

        if self.budget_type:
            domain.append(('budget_type', '=', self.budget_type))

        return domain

    def _group_move_data(self, moves, appropriation_only=False, net_calculation=False, disbursed_only=False, obligated_only=False):
        """Group budget move data by account and analytics"""
        result = defaultdict(float)

        for move in moves:
            for line in move.line_ids.filtered(lambda l: not l.is_virtual_line):
                if not self._move_line_matches_filters(line):
                    continue

                key = self._get_grouping_key_move(line)
                amount = abs(line.balance)

                if appropriation_only and move.move_type == 'appropriation':
                    result[key] += amount
                elif net_calculation:
                    if move.move_type == 'appropriation':
                        result[key] += amount
                    else:
                        result[key] -= amount
                elif disbursed_only and move.move_type == 'entry':
                    result[key] += amount
                elif obligated_only and move.move_type == 'consume':
                    result[key] += amount

        return dict(result)

    def _get_grouping_key_move(self, line):
        """Generate grouping key for budget move lines"""
        return (
            line.account_id.id,
            line.activity_analytic_id.id if line.activity_analytic_id else 0,
            line.department_analytic_id.id if line.department_analytic_id else 0,
            line.fund_analytic_id.id if line.fund_analytic_id else 0,
            line.source_analytic_id.id if line.source_analytic_id else 0,
        )

    def _get_grouping_key_commitment(self, line):
        """Generate grouping key for commitment lines"""
        return (
            line.account_id.id,
            line.activity_analytic_id.id if line.activity_analytic_id else 0,
            line.department_analytic_id.id if line.department_analytic_id else 0,
            line.fund_analytic_id.id if line.fund_analytic_id else 0,
            line.source_analytic_id.id if line.source_analytic_id else 0,
        )

    def _move_line_matches_filters(self, line):
        """Check if budget move line matches report filters"""
        # Check analytic filters
        if self.activity_analytic_ids and line.activity_analytic_id not in self.activity_analytic_ids:
            return False

        if self.department_analytic_ids and line.department_analytic_id not in self.department_analytic_ids:
            return False

        if self.fund_analytic_ids and line.fund_analytic_id not in self.fund_analytic_ids:
            return False

        if self.source_analytic_ids and line.source_analytic_id not in self.source_analytic_ids:
            return False

        if self.budget_account_ids and line.account_id not in self.budget_account_ids:
            return False

        return True

    def _line_matches_filters(self, line):
        """Check if commitment line matches report filters"""
        # Check analytic filters
        if self.activity_analytic_ids and line.activity_analytic_id not in self.activity_analytic_ids:
            return False

        if self.fund_analytic_ids and line.fund_analytic_id not in self.fund_analytic_ids:
            return False

        if self.budget_account_ids and line.account_id not in self.budget_account_ids:
            return False

        return True

    def action_export_excel(self):
        """Export report to Excel"""
        # This could be implemented with xlsxwriter or similar
        return {
            'type': 'ir.actions.act_url',
            'url': f'/budget/execution_status/export/excel/{self.id}',
            'target': 'new',
        }

    def action_print_report(self):
        """Print the report as PDF"""
        return self.env.ref('budget.budget_execution_status_report_print').report_action(self)
