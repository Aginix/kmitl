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

        # Get all activities and funds from complete hierarchy
        activities_hierarchy = self._get_complete_activities_hierarchy(line_data_by_activity.keys())
        funds_hierarchy = self._get_complete_funds_hierarchy(line_data_by_activity)
        
        # Build complete hierarchy with roll-up calculations
        hierarchy = []
        
        for activity_info in activities_hierarchy:
            activity_node = {
                "type": "activity",
                "id": f"activity_{activity_info['id']}",
                "name": activity_info['name'],
                "code": activity_info['code'],
                "complete_name": activity_info['complete_name'],
                "children": [],
                "total_amount": 0,
            }
            
            # Add funds to this activity
            for fund_info in funds_hierarchy:
                fund_node = {
                    "type": "fund",
                    "id": f"fund_{fund_info['id']}",
                    "name": fund_info['name'],
                    "code": fund_info['code'],
                    "children": [],
                    "total_amount": 0,
                }
                
                # Check if this activity-fund combination has data
                activity_id = activity_info['id'] if activity_info['id'] != 'no_activity' else None
                fund_id = fund_info['id'] if fund_info['id'] != 'no_fund' else None
                
                if activity_id in line_data_by_activity and fund_id in line_data_by_activity[activity_id]:
                    account_groups = line_data_by_activity[activity_id][fund_id]
                    
                    # Build account level
                    for account_key, line_list in account_groups.items():
                        if account_key:
                            account = self.env['budget.account'].browse(account_key)
                            account_node = {
                                "type": "account",
                                "id": f"account_{account.id}",
                                "name": account.name,
                                "code": account.code,
                                "children": [],
                                "total_amount": 0,
                            }
                        else:
                            account_node = {
                                "type": "account",
                                "id": "account_no_account",
                                "name": "ไม่ระบุรหัสงบประมาณ",
                                "code": "",
                                "children": [],
                                "total_amount": 0,
                            }
                        
                        # Add line details
                        for line_info in line_list:
                            line_node = {
                                "type": "line",
                                "id": f"line_{line_info['id']}",
                                "balance": line_info['balance'],
                                "note": line_info['note'],
                                "account_info": line_info['account'],
                            }
                            account_node["children"].append(line_node)
                            account_node["total_amount"] += line_info['balance']
                        
                        fund_node["children"].append(account_node)
                        fund_node["total_amount"] += account_node["total_amount"]
                
                # Only add fund node if it has children or if we want to show empty structure
                if fund_node["children"]:
                    activity_node["children"].append(fund_node)
                    activity_node["total_amount"] += fund_node["total_amount"]
            
            # Only add activity node if it has children
            if activity_node["children"]:
                hierarchy.append(activity_node)
        
        # Sort hierarchy by activity code
        hierarchy.sort(key=lambda x: x.get('code', ''))
        
        return hierarchy

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