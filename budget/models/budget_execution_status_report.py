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
            for line in move.line_ids:
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

    # API Methods for Owl Component
    @api.model
    def get_filter_options(self):
        """Get available filter options for the interactive report"""
        try:
            # Get fiscal years
            fiscal_years = self.env['account.fiscal.year'].search([])
            fiscal_year_data = []
            for fy in fiscal_years:
                fiscal_year_data.append({
                    'id': fy.id,
                    'name': fy.name,
                    'date_start': fy.date_from.isoformat() if fy.date_from else None,
                    'date_end': fy.date_to.isoformat() if fy.date_to else None,
                    'is_current': self._is_current_fiscal_year(fy)
                })

            # Get analytic accounts by plan
            activities = self.env['account.analytic.account'].search([
                ('root_plan_id.code', '=', 'activities')
            ])
            departments = self.env['account.analytic.account'].search([
                ('root_plan_id.code', '=', 'departments')
            ])
            funds = self.env['account.analytic.account'].search([
                ('root_plan_id.code', '=', 'funds')
            ])
            sources = self.env['account.analytic.account'].search([
                ('root_plan_id.code', '=', 'sources')
            ])

            # Get budget accounts
            budget_accounts = self.env['budget.account'].search([])

            return {
                'fiscal_years': fiscal_year_data,
                'activities': [{'id': a.id, 'name': a.name, 'code': a.code} for a in activities],
                'departments': [{'id': d.id, 'name': d.name, 'code': d.code} for d in departments],
                'funds': [{'id': f.id, 'name': f.name, 'code': f.code} for f in funds],
                'sources': [{'id': s.id, 'name': s.name, 'code': s.code} for s in sources],
                'budget_accounts': [{'id': ba.id, 'name': ba.name, 'code': ba.code} for ba in budget_accounts],
            }
        except Exception as e:
            _logger.error(f"Error getting filter options: {str(e)}")
            return {
                'fiscal_years': [],
                'activities': [],
                'departments': [],
                'funds': [],
                'sources': [],
                'budget_accounts': [],
            }

    @api.model
    def get_interactive_report_data(self, filters):
        """Get report data for interactive Owl component with hierarchical structure"""
        try:
            # Create temporary report record with filters
            filter_vals = self._prepare_filters_from_dict(filters)
            report = self.create(filter_vals)

            # Generate report data
            report.action_generate_report()

            # Prepare summary data
            summary_data = {
                'total_initial_appropriation': report.total_initial_appropriation,
                'total_current_budget': report.total_current_budget,
                'total_requested': report.total_requested,
                'total_reserved': report.total_reserved,
                'total_obligated': report.total_obligated,
                'total_disbursed': report.total_disbursed,
                'total_used': report.total_used,
                'total_remaining': report.total_remaining,
                'total_returned': report.total_returned,
                'utilization_percentage': (report.total_used / report.total_current_budget * 100) if report.total_current_budget else 0
            }

            # Build hierarchical data with complete parent paths
            hierarchical_data = report._build_hierarchical_data_with_paths()

            return {
                'summary': summary_data,
                'hierarchical_data': hierarchical_data
            }

        except Exception as e:
            _logger.error(f"Error generating interactive report data: {str(e)}")
            raise UserError(_("Error generating report data: %s") % str(e))

    def _prepare_filters_from_dict(self, filters):
        """Convert frontend filters dict to model field values"""
        from datetime import datetime

        # Ensure we have valid dates - fallback to current fiscal year or year
        date_from = filters.get('date_from')
        date_to = filters.get('date_to')

        # Convert string dates to date objects if needed
        if isinstance(date_from, str) and date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            except ValueError:
                date_from = None

        if isinstance(date_to, str) and date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                date_to = None

        if not date_from or not date_to:
            # Try to get from fiscal year
            fy_id = filters.get('date_range_fy_id')
            if fy_id:
                fy = self.env['account.fiscal.year'].browse(fy_id)
                if fy.exists():
                    date_from = fy.date_from
                    date_to = fy.date_to

            # If still no dates, use current year
            if not date_from or not date_to:
                today = fields.Date.today()
                date_from = today.replace(month=1, day=1)
                date_to = today.replace(month=12, day=31)

        vals = {
            'name': f"Interactive Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'date_from': date_from,
            'date_to': date_to,
            'date_range_fy_id': filters.get('date_range_fy_id'),
            'budget_type': filters.get('budget_type', 'expense'),
        }

        # Handle Many2many fields
        if filters.get('activity_analytic_ids'):
            vals['activity_analytic_ids'] = [(6, 0, filters['activity_analytic_ids'])]
        if filters.get('department_analytic_ids'):
            vals['department_analytic_ids'] = [(6, 0, filters['department_analytic_ids'])]
        if filters.get('fund_analytic_ids'):
            vals['fund_analytic_ids'] = [(6, 0, filters['fund_analytic_ids'])]
        if filters.get('source_analytic_ids'):
            vals['source_analytic_ids'] = [(6, 0, filters['source_analytic_ids'])]
        if filters.get('budget_account_ids'):
            vals['budget_account_ids'] = [(6, 0, filters['budget_account_ids'])]

        return vals

    def _is_current_fiscal_year(self, fiscal_year):
        """Check if fiscal year contains today's date"""
        today = fields.Date.today()
        return fiscal_year.date_from <= today <= fiscal_year.date_to

    def _build_hierarchical_data_with_paths(self):
        """Build hierarchical data with complete parent paths for activities and funds"""
        if not self.line_ids:
            return []

        # Use the same approach as budget appropriation overview
        # Collect all unique analytic account IDs from lines
        all_analytic_ids = set()
        all_budget_account_ids = set()

        for line in self.line_ids:
            if line.activity_analytic_id:
                all_analytic_ids.add(line.activity_analytic_id.id)
            if line.fund_analytic_id:
                all_analytic_ids.add(line.fund_analytic_id.id)
            if line.budget_account_id:
                all_budget_account_ids.add(line.budget_account_id.id)

        # Get ALL analytic accounts in the hierarchy paths (including all parents)
        expanded_analytic_ids = self._get_all_hierarchy_analytic_ids(all_analytic_ids)

        # Get complete hierarchy paths
        hierarchy_paths = self._get_complete_hierarchy_paths(expanded_analytic_ids)
        budget_account_paths = self._get_budget_account_hierarchy_paths(all_budget_account_ids)

        # Build line data with paths
        line_data_with_paths = []

        for line in self.line_ids:
            # Get complete paths for this line's analytic accounts
            paths = {
                'activity': self._get_path_hierarchy(line.activity_analytic_id, hierarchy_paths) if line.activity_analytic_id else [],
                'fund': self._get_path_hierarchy(line.fund_analytic_id, hierarchy_paths) if line.fund_analytic_id else [],
            }

            # Get budget account hierarchy path
            budget_account_path = []
            if line.budget_account_id and line.budget_account_id.id in budget_account_paths:
                if line.budget_account_id.parent_path:
                    path_ids = [int(id_str) for id_str in line.budget_account_id.parent_path.strip('/').split('/') if id_str]
                    for account_id in path_ids:
                        if account_id in budget_account_paths:
                            budget_account_path.append(budget_account_paths[account_id])
                else:
                    budget_account_path.append(budget_account_paths[line.budget_account_id.id])

            line_data = {
                "id": line.id,
                "account": {
                    "id": line.budget_account_id.id,
                    "name": line.budget_account_id.name,
                    "code": line.budget_account_id.code,
                },
                "budget_account_path": budget_account_path,
                "initial_appropriation": line.initial_appropriation or 0,
                "current_budget": line.current_budget or 0,
                "total_requested": line.total_requested or 0,
                "reserved_amount": line.reserved_amount or 0,
                "obligated_amount": line.obligated_amount or 0,
                "disbursed_amount": line.disbursed_amount or 0,
                "total_used": line.total_used or 0,
                "remaining_budget": line.remaining_budget or 0,
                "returned_amount": line.returned_amount or 0,
                "paths": paths
            }

            line_data_with_paths.append(line_data)

        # Build complete hierarchy tree including all parent nodes
        return self._build_complete_hierarchy_tree(line_data_with_paths, hierarchy_paths)

    def _get_all_hierarchy_analytic_ids(self, line_analytic_ids):
        """Get all analytic account IDs that should be included in hierarchy (including all parents)"""
        if not line_analytic_ids:
            return set()

        # Start with line analytic IDs
        analytic_accounts = self.env['account.analytic.account'].browse(list(line_analytic_ids))
        all_related_ids = set(line_analytic_ids)

        # For each account, add all its parents from parent_path
        for account in analytic_accounts:
            if account.parent_path:
                # Extract all IDs from parent_path (format: "1/2/3/")
                path_ids = [int(id_str) for id_str in account.parent_path.strip('/').split('/') if id_str]
                all_related_ids.update(path_ids)

        return all_related_ids

    def _get_complete_hierarchy_paths(self, analytic_ids):
        """Get complete hierarchy paths for analytic accounts using parent_path"""
        if not analytic_ids:
            return {}

        # Get all related analytic accounts (including parents) using parent_path
        analytic_accounts = self.env['account.analytic.account'].browse(list(analytic_ids))
        all_related_ids = set()

        for account in analytic_accounts:
            if account.parent_path:
                # Extract all IDs from parent_path (format: "1/2/3/")
                path_ids = [int(id_str) for id_str in account.parent_path.strip('/').split('/') if id_str]
                all_related_ids.update(path_ids)
            else:
                all_related_ids.add(account.id)

        # Fetch all related accounts with their hierarchy information
        all_accounts = self.env['account.analytic.account'].browse(list(all_related_ids))

        # Build hierarchy mapping
        hierarchy_map = {}
        for account in all_accounts:
            hierarchy_map[account.id] = {
                'id': account.id,
                'name': account.name,
                'code': account.code or '',
                'parent_id': account.parent_id.id if account.parent_id else None,
                'parent_path': account.parent_path or '',
                'root_plan_code': account.root_plan_id.code if account.root_plan_id else '',
                'level': len(account.parent_path.strip('/').split('/')) if account.parent_path else 1
            }

        return hierarchy_map

    def _get_path_hierarchy(self, analytic_account, hierarchy_map):
        """Get complete path hierarchy for a specific analytic account"""
        if not analytic_account or analytic_account.id not in hierarchy_map:
            return []

        path = []
        if analytic_account.parent_path:
            # Extract path IDs and build hierarchy
            path_ids = [int(id_str) for id_str in analytic_account.parent_path.strip('/').split('/') if id_str]
            for account_id in path_ids:
                if account_id in hierarchy_map:
                    path.append(hierarchy_map[account_id])
        else:
            # Single account without parents
            path.append(hierarchy_map[analytic_account.id])

        return path

    def _get_budget_account_hierarchy_paths(self, account_ids):
        """Get complete hierarchy paths for budget accounts using parent_path"""
        if not account_ids:
            return {}

        # Get all related budget accounts (including parents) using parent_path
        budget_accounts = self.env['budget.account'].browse(list(account_ids))
        all_related_ids = set()

        for account in budget_accounts:
            if account.parent_path:
                # Extract all IDs from parent_path (format: "1/2/3/")
                path_ids = [int(id_str) for id_str in account.parent_path.strip('/').split('/') if id_str]
                all_related_ids.update(path_ids)
            else:
                all_related_ids.add(account.id)

        # Fetch all related accounts with their hierarchy information
        all_accounts = self.env['budget.account'].browse(list(all_related_ids))

        # Build hierarchy mapping
        hierarchy_map = {}
        for account in all_accounts:
            hierarchy_map[account.id] = {
                'id': account.id,
                'name': account.name,
                'code': account.code or '',
                'parent_id': account.parent_id.id if account.parent_id else None,
                'parent_path': account.parent_path or '',
                'level': len(account.parent_path.strip('/').split('/')) if account.parent_path else 1
            }

        return hierarchy_map

    def _build_complete_hierarchy_tree(self, line_data_with_paths, hierarchy_paths):
        """Build complete hierarchy tree including all parent nodes, similar to budget appropriation overview"""

        # Step 1: Identify root nodes for activities
        activity_roots = set()

        for account_id, account_data in hierarchy_paths.items():
            if account_data['root_plan_code'] == 'activities':
                # Find root activities (level 1 in hierarchy)
                if account_data['level'] == 1:
                    activity_roots.add(account_id)

        # Step 2: Build complete tree structure starting from activity roots
        root_nodes = {}

        # Build activity hierarchy first (complete tree structure)
        for root_id in activity_roots:
            if root_id in hierarchy_paths:
                root_data = hierarchy_paths[root_id]
                self._build_node_tree(root_data, hierarchy_paths, root_nodes, "activity")

        # Step 3: For each line, place it in the correct position in the tree
        for line_data in line_data_with_paths:
            self._place_line_in_tree(line_data, root_nodes, hierarchy_paths)

        # Step 4: Calculate totals from bottom up and convert to list
        result = list(root_nodes.values())
        self._calculate_tree_totals(result)

        return result

    def _build_node_tree(self, node_data, hierarchy_paths, parent_dict, node_type_prefix):
        """Recursively build node tree structure"""
        node_key = f"{node_type_prefix}_{node_data['code']}"

        if node_key not in parent_dict:
            parent_dict[node_key] = {
                "key": node_key,
                "type": node_type_prefix,
                "level": node_data['level'],
                "name": node_data['name'],
                "code": node_data['code'],
                "id": node_data['id'],
                "children": {},
                "totals": {
                    "initial_appropriation": 0,
                    "current_budget": 0,
                    "total_requested": 0,
                    "reserved_amount": 0,
                    "obligated_amount": 0,
                    "disbursed_amount": 0,
                    "total_used": 0,
                    "remaining_budget": 0,
                    "returned_amount": 0
                },
                "utilization": 0,
                "expanded": False,
            }

        # Find and add children
        for child_id, child_data in hierarchy_paths.items():
            if child_data.get('parent_id') == node_data['id'] and child_data['root_plan_code'] == node_data['root_plan_code']:
                self._build_node_tree(child_data, hierarchy_paths, parent_dict[node_key]["children"], node_type_prefix)

    def _place_line_in_tree(self, line_data, root_nodes, hierarchy_paths):
        """Place a line in the correct position in the tree structure"""
        activity_path = line_data['paths'].get('activity', [])
        fund_path = line_data['paths'].get('fund', [])

        # Navigate to the correct activity node
        current_level = root_nodes
        for activity_node in activity_path:
            activity_key = f"activity_{activity_node['code']}"
            if activity_key in current_level:
                current_level = current_level[activity_key]["children"]
            else:
                return  # Activity not found

        # Navigate/create fund hierarchy
        for i, fund_node in enumerate(fund_path):
            fund_key = f"fund_{fund_node['code']}"

            if fund_key not in current_level:
                # Create fund node if it doesn't exist
                current_level[fund_key] = {
                    "key": fund_key,
                    "type": "fund",
                    "level": len(activity_path) + fund_node['level'],
                    "name": fund_node['name'],
                    "code": fund_node['code'],
                    "id": fund_node['id'],
                    "children": {},
                    "totals": {
                        "initial_appropriation": 0,
                        "current_budget": 0,
                        "total_requested": 0,
                        "reserved_amount": 0,
                        "obligated_amount": 0,
                        "disbursed_amount": 0,
                        "total_used": 0,
                        "remaining_budget": 0,
                        "returned_amount": 0
                    },
                    "utilization": 0,
                    "expanded": False,
                }

            current_level = current_level[fund_key]["children"]

        # Add budget account and line data
        if line_data['budget_account_path']:
            for j, account_node in enumerate(line_data['budget_account_path']):
                account_key = f"account_{account_node['code']}"

                if account_key not in current_level:
                    current_level[account_key] = {
                        "key": account_key,
                        "type": "account",
                        "level": len(activity_path) + len(fund_path) + j + 1,
                        "name": account_node['name'],
                        "code": account_node['code'],
                        "id": account_node['id'],
                        "children": {},
                        "totals": {
                            "initial_appropriation": 0,
                            "current_budget": 0,
                            "total_requested": 0,
                            "reserved_amount": 0,
                            "obligated_amount": 0,
                            "disbursed_amount": 0,
                            "total_used": 0,
                            "remaining_budget": 0,
                            "returned_amount": 0
                        },
                        "utilization": 0,
                        "expanded": False,
                        "line_details": []
                    }

                # Add line data to the account
                if j == len(line_data['budget_account_path']) - 1:  # Last account in path
                    current_level[account_key]["line_details"].append({
                        "id": line_data['id'],
                        "initial_appropriation": line_data['initial_appropriation'],
                        "current_budget": line_data['current_budget'],
                        "total_requested": line_data['total_requested'],
                        "reserved_amount": line_data['reserved_amount'],
                        "obligated_amount": line_data['obligated_amount'],
                        "disbursed_amount": line_data['disbursed_amount'],
                        "total_used": line_data['total_used'],
                        "remaining_budget": line_data['remaining_budget'],
                        "returned_amount": line_data['returned_amount'],
                    })

                    # Add line amounts to account totals
                    for field in ['initial_appropriation', 'current_budget', 'total_requested',
                                'reserved_amount', 'obligated_amount', 'disbursed_amount',
                                'total_used', 'remaining_budget', 'returned_amount']:
                        current_level[account_key]['totals'][field] += line_data[field]

                current_level = current_level[account_key]["children"]

    def _calculate_tree_totals(self, nodes):
        """Calculate totals from children to parents"""
        for node in nodes:
            if isinstance(node["children"], dict):
                # Convert children dict to list and process
                children_list = list(node["children"].values())
                node["children"] = children_list

                # Recursively calculate children totals first
                self._calculate_tree_totals(children_list)

                # Sum up children totals
                for child in children_list:
                    for field in ['initial_appropriation', 'current_budget', 'total_requested',
                                'reserved_amount', 'obligated_amount', 'disbursed_amount',
                                'total_used', 'remaining_budget', 'returned_amount']:
                        node['totals'][field] += child['totals'][field]

                # Calculate utilization
                if node['totals']['current_budget'] > 0:
                    node['utilization'] = (node['totals']['total_used'] / node['totals']['current_budget']) * 100
