import logging
from collections import defaultdict

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class BudgetAppropriationF5Report(models.TransientModel):
    _name = "budget.appropriation.f5.report"
    _description = "Budget Appropriation F5 Report"

    appropriation_id = fields.Many2one("budget.appropriation", string="Budget Appropriation", required=True)

    @api.model
    def get_f5_data(self, appropriation_id, options=None):
        """Generate F5 hierarchical data for single budget appropriation"""
        if options is None:
            options = {}
        
        appropriation = self.env["budget.appropriation"].browse(appropriation_id)
        
        if not appropriation:
            return {"error": "Invalid appropriation"}
        
        # Validate EXPENSE type only
        if appropriation.budget_type != 'expense':
            return {"error": "F5 report is only available for expense type appropriations"}
        
        # Get appropriation lines
        lines = appropriation.line_ids
        
        # Build hierarchy: Activities → Funds → Budget Accounts → Lines
        hierarchy = self._build_hierarchy(lines)
        
        # Calculate totals
        total_amount = sum(line.balance for line in lines)
        
        return {
            "appropriation": {
                "id": appropriation.id,
                "name": appropriation.name,
                "date": appropriation.date.strftime("%d/%m/%Y") if appropriation.date else "",
                "state": appropriation.state,
                "total_amount": total_amount,
                "currency_symbol": appropriation.currency_id.symbol or "฿",
                "fiscal_year": {
                    "id": appropriation.date_range_fy_id.id,
                    "name": appropriation.date_range_fy_id.name,
                } if appropriation.date_range_fy_id else None,
                "department": {
                    "id": appropriation.department_analytic_id.id,
                    "name": appropriation.department_analytic_id.name,
                    "code": appropriation.department_analytic_id.code,
                    "complete_name": self._get_complete_name_without_codes(appropriation.department_analytic_id),
                } if appropriation.department_analytic_id else None,
                "source": {
                    "id": appropriation.source_analytic_id.id,
                    "name": appropriation.source_analytic_id.name,
                    "code": appropriation.source_analytic_id.code,
                } if appropriation.source_analytic_id else None,
                "journal": {
                    "id": appropriation.journal_id.id,
                    "name": appropriation.journal_id.name,
                } if appropriation.journal_id else None,
            },
            "hierarchy": hierarchy,
            "summary": {
                "total_lines": len(lines),
                "total_amount": total_amount,
                "activities_count": len(hierarchy),
            }
        }

    def _build_hierarchy(self, lines):
        """Build complete hierarchical structure from root with roll-up calculations"""
        # First, collect all data from lines
        line_data_by_activity = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        for line in lines:
            activity_key = line.activity_analytic_id.id if line.activity_analytic_id else None
            fund_key = line.fund_analytic_id.id if line.fund_analytic_id else None
            account_key = line.account_id.id if line.account_id else None
            
            line_data_by_activity[activity_key][fund_key][account_key].append({
                "id": line.id,
                "balance": line.balance,
                "note": line.note or "",
                "account": {
                    "id": line.account_id.id,
                    "name": line.account_id.name,
                    "code": line.account_id.code,
                } if line.account_id else None,
            })

        # Build hierarchical structure starting from root activities
        hierarchy = []
        
        # Get all activities used
        used_activity_ids = set(k for k in line_data_by_activity.keys() if k)
        
        if not used_activity_ids:
            return []
        
        # Get root activities that have data (directly or through descendants)
        root_activities = self._get_root_activities_with_data(used_activity_ids)
        
        for root_activity in root_activities:
            activity_node = self._build_activity_hierarchy_recursive(root_activity, line_data_by_activity, used_activity_ids)
            if activity_node:
                hierarchy.append(activity_node)
        
        return hierarchy

    def _get_root_activities_with_data(self, used_activity_ids):
        """Get root activities that have data (directly or through descendants)"""
        all_activities_with_data = set()
        
        # Get all activities that have data and their parents
        for activity_id in used_activity_ids:
            activity = self.env['account.analytic.account'].browse(activity_id)
            current = activity
            while current:
                all_activities_with_data.add(current.id)
                current = current.parent_id
        
        # Get all activity records
        activities = self.env['account.analytic.account'].browse(list(all_activities_with_data))
        activities = activities.filtered(lambda a: a.root_plan_id.code == 'activities')
        
        # Return only root activities (those without parent)
        root_activities = activities.filtered(lambda a: not a.parent_id)
        return root_activities.sorted('code')

    def _build_activity_hierarchy_recursive(self, activity, line_data_by_activity, used_activity_ids):
        """Recursively build activity hierarchy with proper parent-child structure"""
        activity_node = {
            "type": "activity",
            "key": f"activity_{activity.id}",
            "id": activity.id,
            "name": activity.name,
            "code": activity.code or '',
            "complete_name": self._get_complete_name_without_codes(activity),
            "children": [],
            "total_amount": 0,
            "level": len(activity.parent_path.split('/')) - 2 if activity.parent_path else 0,
        }
        
        # Check if this activity has direct data
        if activity.id in line_data_by_activity:
            fund_nodes = self._build_funds_hierarchy_for_activity(activity.id, line_data_by_activity[activity.id])
            activity_node["children"].extend(fund_nodes)
            activity_node["total_amount"] += sum(fund["total_amount"] for fund in fund_nodes)
        
        # Add child activities recursively
        for child_activity in activity.child_ids.sorted('code'):
            if self._activity_has_data_recursive(child_activity, used_activity_ids):
                child_node = self._build_activity_hierarchy_recursive(child_activity, line_data_by_activity, used_activity_ids)
                if child_node:
                    activity_node["children"].append(child_node)
                    activity_node["total_amount"] += child_node["total_amount"]
        
        return activity_node if activity_node["children"] else None

    def _activity_has_data_recursive(self, activity, used_activity_ids):
        """Check if activity or any of its descendants have data"""
        if activity.id in used_activity_ids:
            return True
        
        for child in activity.child_ids:
            if self._activity_has_data_recursive(child, used_activity_ids):
                return True
        
        return False

    def _build_funds_hierarchy_for_activity(self, activity_id, funds_data):
        """Build fund hierarchy for a specific activity"""
        fund_nodes = []
        
        # Get all fund IDs used in this activity
        used_fund_ids = set(k for k in funds_data.keys() if k)
        
        if not used_fund_ids:
            return []
        
        # Get root funds that have data
        root_funds = self._get_root_funds_with_data(used_fund_ids)
        
        for root_fund in root_funds:
            fund_node = self._build_fund_hierarchy_recursive(root_fund, funds_data, used_fund_ids)
            if fund_node:
                fund_nodes.append(fund_node)
        
        return fund_nodes

    def _get_root_funds_with_data(self, used_fund_ids):
        """Get root funds that have data (directly or through descendants)"""
        all_funds_with_data = set()
        
        # Get all funds that have data and their parents
        for fund_id in used_fund_ids:
            fund = self.env['account.analytic.account'].browse(fund_id)
            current = fund
            while current:
                all_funds_with_data.add(current.id)
                current = current.parent_id
        
        # Get all fund records
        funds = self.env['account.analytic.account'].browse(list(all_funds_with_data))
        funds = funds.filtered(lambda f: f.root_plan_id.code == 'funds')
        
        # Return only root funds (those without parent)
        root_funds = funds.filtered(lambda f: not f.parent_id)
        return root_funds.sorted('code')

    def _build_fund_hierarchy_recursive(self, fund, funds_data, used_fund_ids):
        """Recursively build fund hierarchy with proper parent-child structure"""
        fund_node = {
            "type": "fund",
            "key": f"fund_{fund.id}",
            "id": fund.id,
            "name": fund.name,
            "code": fund.code or '',
            "children": [],
            "total_amount": 0,
            "level": len(fund.parent_path.split('/')) - 2 if fund.parent_path else 0,
        }
        
        # Check if this fund has direct data
        if fund.id in funds_data:
            account_nodes = self._build_accounts_for_fund(funds_data[fund.id], fund_node["level"])
            fund_node["children"].extend(account_nodes)
            fund_node["total_amount"] += sum(account["total_amount"] for account in account_nodes)
        
        # Add child funds recursively
        for child_fund in fund.child_ids.sorted('code'):
            if self._fund_has_data_recursive(child_fund, used_fund_ids):
                child_node = self._build_fund_hierarchy_recursive(child_fund, funds_data, used_fund_ids)
                if child_node:
                    fund_node["children"].append(child_node)
                    fund_node["total_amount"] += child_node["total_amount"]
        
        return fund_node if fund_node["children"] else None

    def _fund_has_data_recursive(self, fund, used_fund_ids):
        """Check if fund or any of its descendants have data"""
        if fund.id in used_fund_ids:
            return True
        
        for child in fund.child_ids:
            if self._fund_has_data_recursive(child, used_fund_ids):
                return True
        
        return False

    def _build_accounts_for_fund(self, accounts_data, fund_level=0):
        """Build account nodes for a specific fund"""
        account_nodes = []
        
        for account_key, line_list in accounts_data.items():
            if account_key:
                account = self.env['budget.account'].browse(account_key)
                account_node = {
                    "type": "account",
                    "key": f"account_{account.id}",
                    "id": account.id,
                    "name": account.name,
                    "code": account.code,
                    "children": [],
                    "total_amount": sum(line_data['balance'] for line_data in line_list),
                    "line_details": line_list,
                    "level": fund_level + 1,  # Account level is one level deeper than fund
                }
            else:
                account_node = {
                    "type": "account",
                    "key": "account_no_account",
                    "id": "no_account",
                    "name": "ไม่ระบุรหัสงบประมาณ",
                    "code": "",
                    "children": [],
                    "total_amount": sum(line_data['balance'] for line_data in line_list),
                    "line_details": line_list,
                    "level": fund_level + 1,
                }
            
            account_nodes.append(account_node)
        
        return account_nodes

    def _get_complete_activities_hierarchy(self, used_activity_ids):
        """Get complete activities hierarchy including all parents"""
        # Get activities that have data
        used_activities = set()
        for activity_id in used_activity_ids:
            if activity_id:
                used_activities.add(activity_id)
        
        if not used_activities:
            return [{
                'id': 'no_activity',
                'name': 'ไม่ระบุกิจกรรม',
                'code': '',
                'complete_name': 'ไม่ระบุกิจกรรม'
            }]
        
        # Get all parent activities for used activities
        all_activities = set()
        for activity_id in used_activities:
            activity = self.env['account.analytic.account'].browse(activity_id)
            # Add current and all parents
            current = activity
            while current:
                all_activities.add(current.id)
                current = current.parent_id
        
        # Get activity records
        activities = self.env['account.analytic.account'].browse(list(all_activities))
        activities = activities.filtered(lambda a: a.root_plan_id.code == 'activities')
        
        # Build hierarchy starting from root
        root_activities = activities.filtered(lambda a: not a.parent_id)
        
        hierarchy = []
        for root_activity in root_activities.sorted('code'):
            self._add_activity_to_hierarchy(root_activity, hierarchy, used_activities)
        
        return hierarchy

    def _add_activity_to_hierarchy(self, activity, hierarchy, used_activities):
        """Recursively add activity and its children if they have data"""
        # Check if this activity or any of its descendants have data
        if self._activity_has_data(activity, used_activities):
            activity_info = {
                'id': activity.id,
                'name': activity.name,
                'code': activity.code or '',
                'complete_name': self._get_complete_name_without_codes(activity)
            }
            hierarchy.append(activity_info)
            
            # Add children recursively
            for child in activity.child_ids.sorted('code'):
                self._add_activity_to_hierarchy(child, hierarchy, used_activities)

    def _activity_has_data(self, activity, used_activities):
        """Check if activity or any of its descendants have data"""
        # Direct check
        if activity.id in used_activities:
            return True
        
        # Check descendants
        for child in activity.child_ids:
            if self._activity_has_data(child, used_activities):
                return True
        
        return False

    def _get_complete_funds_hierarchy(self, line_data_by_activity):
        """Get complete funds hierarchy"""
        # Get all fund IDs used in the data
        used_fund_ids = set()
        for activity_data in line_data_by_activity.values():
            for fund_id in activity_data.keys():
                if fund_id:
                    used_fund_ids.add(fund_id)
        
        if not used_fund_ids:
            return [{
                'id': 'no_fund',
                'name': 'ไม่ระบุกองทุน',
                'code': ''
            }]
        
        # Get all parent funds for used funds
        all_funds = set()
        for fund_id in used_fund_ids:
            fund = self.env['account.analytic.account'].browse(fund_id)
            # Add current and all parents
            current = fund
            while current:
                all_funds.add(current.id)
                current = current.parent_id
        
        # Get fund records
        funds = self.env['account.analytic.account'].browse(list(all_funds))
        funds = funds.filtered(lambda f: f.root_plan_id.code == 'funds')
        
        # Build flat list of funds with hierarchy order
        hierarchy = []
        root_funds = funds.filtered(lambda f: not f.parent_id)
        
        for root_fund in root_funds.sorted('code'):
            self._add_fund_to_hierarchy(root_fund, hierarchy, used_fund_ids)
        
        return hierarchy

    def _add_fund_to_hierarchy(self, fund, hierarchy, used_fund_ids):
        """Recursively add fund and its children if they have data"""
        # Check if this fund or any of its descendants have data
        if self._fund_has_data(fund, used_fund_ids):
            fund_info = {
                'id': fund.id,
                'name': fund.name,
                'code': fund.code or ''
            }
            hierarchy.append(fund_info)
            
            # Add children recursively
            for child in fund.child_ids.sorted('code'):
                self._add_fund_to_hierarchy(child, hierarchy, used_fund_ids)

    def _fund_has_data(self, fund, used_fund_ids):
        """Check if fund or any of its descendants have data"""
        # Direct check
        if fund.id in used_fund_ids:
            return True
        
        # Check descendants
        for child in fund.child_ids:
            if self._fund_has_data(child, used_fund_ids):
                return True
        
        return False

    def _get_complete_name_without_codes(self, analytic_account):
        """Get complete name without codes for display"""
        if not analytic_account:
            return ""
        
        names = []
        current = analytic_account
        while current:
            # Remove code from name if it exists
            name = current.name
            if current.code and name.startswith(current.code):
                name = name[len(current.code):].strip()
                if name.startswith('-') or name.startswith('.'):
                    name = name[1:].strip()
            names.append(name)
            current = current.parent_id
        
        # Reverse to get root → leaf order
        names.reverse()
        return " > ".join(names)