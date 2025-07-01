import logging
from collections import defaultdict
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_datetime

_logger = logging.getLogger(__name__)


class BudgetReport(models.TransientModel):
    _name = "budget.report"
    _description = "Generic Budget Report"

    # Report Configuration
    name = fields.Char(
        string="Report Name",
        required=True,
        default="Budget Report",
    )

    report_type = fields.Selection(
        selection=[
            ("budget_vs_actual", "Budget vs Actual"),
            ("commitment_analysis", "Commitment Analysis"),
            ("fund_analysis", "Fund Analysis"),
            ("department_analysis", "Department Analysis"),
            ("activity_analysis", "Activity Analysis"),
            ("budget_availability", "Budget Availability"),
            ("hierarchical_view", "Hierarchical View"),
        ],
        string="Report Type",
        required=True,
        default="budget_vs_actual",
    )

    # Date Filters
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

    # Analytic Filters (Multi-dimensional)
    activity_analytic_ids = fields.Many2many(
        "account.analytic.account",
        "budget_report_activity_rel",
        "report_id",
        "analytic_id",
        string="Activities",
        domain=[("root_plan_id.code", "=", "activities")],
        help="Filter by specific activities",
    )

    department_analytic_ids = fields.Many2many(
        "account.analytic.account",
        "budget_report_department_rel",
        "report_id",
        "analytic_id",
        string="Departments",
        domain=[("root_plan_id.code", "=", "departments")],
        help="Filter by specific departments",
    )

    fund_analytic_ids = fields.Many2many(
        "account.analytic.account",
        "budget_report_fund_rel",
        "report_id",
        "analytic_id",
        string="Funds",
        domain=[("root_plan_id.code", "=", "funds")],
        help="Filter by specific funds",
    )

    source_analytic_ids = fields.Many2many(
        "account.analytic.account",
        "budget_report_source_rel",
        "report_id",
        "analytic_id",
        string="Sources",
        domain=[("root_plan_id.code", "=", "sources")],
        help="Filter by specific sources",
    )

    # Budget Account Filters
    budget_account_ids = fields.Many2many(
        "budget.account",
        "budget_report_account_rel",
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

    # Display Options
    show_hierarchy = fields.Boolean(
        string="Show Hierarchy",
        default=True,
        help="Display data in hierarchical structure",
    )

    group_by_level = fields.Selection(
        selection=[
            ("activity", "Activity"),
            ("department", "Department"),
            ("fund", "Fund"),
            ("source", "Source"),
            ("account", "Budget Account"),
        ],
        string="Group By",
        default="activity",
        help="Primary grouping level",
    )

    hide_zero_amounts = fields.Boolean(
        string="Hide Zero Amounts",
        default=True,
        help="Hide lines with zero amounts",
    )

    include_commitments = fields.Boolean(
        string="Include Commitments",
        default=True,
        help="Include commitment data in analysis",
    )

    # Report Results
    line_ids = fields.One2many(
        comodel_name="budget.report.line",
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

    # Summary Statistics
    total_budget = fields.Monetary(
        string="Total Budget",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_actual = fields.Monetary(
        string="Total Actual",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_commitment = fields.Monetary(
        string="Total Commitment",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    total_available = fields.Monetary(
        string="Total Available",
        compute="_compute_totals",
        currency_field="currency_id",
    )

    @api.depends("line_ids.budget_amount", "line_ids.actual_amount",
                 "line_ids.commitment_amount", "line_ids.available_amount")
    def _compute_totals(self):
        """Compute summary totals"""
        for report in self:
            report.total_budget = sum(report.line_ids.mapped("budget_amount"))
            report.total_actual = sum(report.line_ids.mapped("actual_amount"))
            report.total_commitment = sum(report.line_ids.mapped("commitment_amount"))
            report.total_available = sum(report.line_ids.mapped("available_amount"))

    def action_generate_report(self):
        """Generate report data based on configured parameters"""
        self.ensure_one()

        # Clear existing lines
        self.line_ids.unlink()

        # Generate new report lines based on report type
        if self.report_type == "budget_vs_actual":
            self._generate_budget_vs_actual()
        elif self.report_type == "commitment_analysis":
            self._generate_commitment_analysis()
        elif self.report_type == "fund_analysis":
            self._generate_fund_analysis()
        elif self.report_type == "department_analysis":
            self._generate_department_analysis()
        elif self.report_type == "activity_analysis":
            self._generate_activity_analysis()
        elif self.report_type == "budget_availability":
            self._generate_budget_availability()
        elif self.report_type == "hierarchical_view":
            self._generate_hierarchical_view()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Report Results'),
            'res_model': 'budget.report',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref('budget.budget_report_form_view').id,
            'target': 'current',
        }

    def _generate_budget_vs_actual(self):
        """Generate budget vs actual comparison"""
        domain = self._build_domain()

        # Get budget move data
        budget_moves = self.env["budget.move"].search(domain)
        grouped_data = self._group_budget_data(budget_moves)

        # Get commitment data if requested
        commitment_data = {}
        if self.include_commitments:
            commitment_data = self._get_commitment_data()

        # Create report lines
        for key, data in grouped_data.items():
            commitment_amount = commitment_data.get(key, 0.0)
            available_amount = data['budget'] - data['actual'] - commitment_amount

            self.env["budget.report.line"].create({
                'report_id': self.id,
                'name': self._format_group_name(key),
                'group_key': str(key),
                'budget_amount': data['budget'],
                'actual_amount': data['actual'],
                'commitment_amount': commitment_amount,
                'available_amount': available_amount,
                'level': 0,
            })

    def _generate_hierarchical_view(self):
        """Generate hierarchical view of budget data"""
        domain = self._build_domain()
        budget_moves = self.env["budget.move"].search(domain)

        # Build hierarchy based on analytic accounts
        hierarchy = self._build_hierarchy_structure(budget_moves)

        # Convert hierarchy to report lines
        self._create_hierarchy_lines(hierarchy)

    def _build_domain(self):
        """Build search domain based on report filters"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'posted'),
        ]

        if self.date_range_fy_id:
            domain.append(('date_range_fy_id', '=', self.date_range_fy_id.id))

        if self.budget_type:
            domain.append(('budget_type', '=', self.budget_type))

        # Add analytic filters
        if self.activity_analytic_ids:
            domain.append(('line_ids.activity_analytic_id', 'in', self.activity_analytic_ids.ids))

        if self.department_analytic_ids:
            domain.append(('department_analytic_id', 'in', self.department_analytic_ids.ids))

        if self.fund_analytic_ids:
            domain.append(('line_ids.fund_analytic_id', 'in', self.fund_analytic_ids.ids))

        if self.source_analytic_ids:
            domain.append(('source_analytic_id', 'in', self.source_analytic_ids.ids))

        if self.budget_account_ids:
            domain.append(('line_ids.account_id', 'in', self.budget_account_ids.ids))

        return domain

    def _group_budget_data(self, budget_moves):
        """Group budget move data by configured grouping"""
        grouped_data = defaultdict(lambda: {'budget': 0.0, 'actual': 0.0})

        for move in budget_moves:
            for line in move.line_ids.filtered(lambda l: not l.is_virtual_line):
                group_key = self._get_group_key(line)

                if move.move_type == 'appropriation':
                    grouped_data[group_key]['budget'] += abs(line.balance)
                else:
                    grouped_data[group_key]['actual'] += abs(line.balance)

        return dict(grouped_data)

    def _get_commitment_data(self):
        """Get commitment data grouped by same logic as budget data"""
        commitment_data = defaultdict(float)

        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ['confirmed', 'reserved']),
        ]

        # Add filters similar to budget domain
        if self.date_range_fy_id:
            domain.append(('date_range_fy_id', '=', self.date_range_fy_id.id))

        commitments = self.env["budget.commitment"].search(domain)

        for commitment in commitments:
            for line in commitment.line_ids:
                # Apply same filtering logic as budget lines
                if self._line_matches_filters(line):
                    group_key = self._get_group_key_commitment(line)
                    commitment_data[group_key] += line.remaining_amount

        return dict(commitment_data)

    def _get_group_key(self, line):
        """Get grouping key for budget move line"""
        if self.group_by_level == 'activity':
            return line.activity_analytic_id.id if line.activity_analytic_id else 0
        elif self.group_by_level == 'department':
            return line.department_analytic_id.id if line.department_analytic_id else 0
        elif self.group_by_level == 'fund':
            return line.fund_analytic_id.id if line.fund_analytic_id else 0
        elif self.group_by_level == 'source':
            return line.source_analytic_id.id if line.source_analytic_id else 0
        elif self.group_by_level == 'account':
            return line.account_id.id if line.account_id else 0
        else:
            return 0

    def _get_group_key_commitment(self, line):
        """Get grouping key for commitment line"""
        if self.group_by_level == 'activity':
            return line.activity_analytic_id.id if line.activity_analytic_id else 0
        elif self.group_by_level == 'department':
            return line.department_analytic_id.id if line.department_analytic_id else 0
        elif self.group_by_level == 'fund':
            return line.fund_analytic_id.id if line.fund_analytic_id else 0
        elif self.group_by_level == 'source':
            return line.source_analytic_id.id if line.source_analytic_id else 0
        elif self.group_by_level == 'account':
            return line.account_id.id if line.account_id else 0
        else:
            return 0

    def _format_group_name(self, group_key):
        """Format display name for group"""
        if not group_key:
            return _("Unassigned")

        if self.group_by_level in ['activity', 'department', 'fund', 'source']:
            analytic = self.env["account.analytic.account"].browse(group_key)
            return f"[{analytic.code}] {analytic.name}" if analytic.code else analytic.name
        elif self.group_by_level == 'account':
            account = self.env["budget.account"].browse(group_key)
            return f"[{account.code}] {account.name}" if account.code else account.name

        return str(group_key)

    def _line_matches_filters(self, line):
        """Check if line matches report filters"""
        # This would implement detailed line filtering logic
        # For now, return True as placeholder
        return True

    def _build_hierarchy_structure(self, budget_moves):
        """Build hierarchical data structure"""
        # Placeholder for hierarchy building logic
        # This would implement the same logic as existing budget_appropriation_report
        # but in a more generic way
        return {}

    def _create_hierarchy_lines(self, hierarchy):
        """Create report lines from hierarchy structure"""
        # Placeholder for hierarchy line creation
        pass

    # Additional report generation methods for other report types
    def _generate_commitment_analysis(self):
        """Generate commitment-focused analysis"""
        pass

    def _generate_fund_analysis(self):
        """Generate fund-based analysis"""
        pass

    def _generate_department_analysis(self):
        """Generate department-based analysis"""
        pass

    def _generate_activity_analysis(self):
        """Generate activity-based analysis"""
        pass

    def _generate_budget_availability(self):
        """Generate budget availability report"""
        pass

    def action_export_excel(self):
        """Export report to Excel"""
        # Placeholder for Excel export functionality
        raise UserError(_("Excel export not yet implemented"))

    def action_export_pdf(self):
        """Export report to PDF"""
        # Placeholder for PDF export functionality
        raise UserError(_("PDF export not yet implemented"))

    def action_print_report(self):
        """Print the report"""
        return self.env.ref('budget_report_print').report_action(self)
