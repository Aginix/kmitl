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
        """Build hierarchical structure: Activities → Funds → Budget Accounts → Lines"""
        # Group lines by activity → fund → account
        activity_groups = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
        for line in lines:
            activity_key = line.activity_analytic_id.id if line.activity_analytic_id else 'no_activity'
            fund_key = line.fund_analytic_id.id if line.fund_analytic_id else 'no_fund'
            account_key = line.account_id.id if line.account_id else 'no_account'
            
            activity_groups[activity_key][fund_key][account_key].append({
                "id": line.id,
                "balance": line.balance,
                "note": line.note or "",
                "account": {
                    "id": line.account_id.id,
                    "name": line.account_id.name,
                    "code": line.account_id.code,
                } if line.account_id else None,
            })

        # Build hierarchy
        hierarchy = []
        
        for activity_key, fund_groups in activity_groups.items():
            # Get activity info
            if activity_key != 'no_activity':
                activity = self.env['account.analytic.account'].browse(activity_key)
                activity_node = {
                    "type": "activity",
                    "id": f"activity_{activity.id}",
                    "name": activity.name,
                    "code": activity.code,
                    "complete_name": self._get_complete_name_without_codes(activity),
                    "children": [],
                    "total_amount": 0,
                }
            else:
                activity_node = {
                    "type": "activity",
                    "id": "activity_no_activity",
                    "name": "ไม่ระบุกิจกรรม",
                    "code": "",
                    "complete_name": "ไม่ระบุกิจกรรม",
                    "children": [],
                    "total_amount": 0,
                }
            
            # Build fund level
            for fund_key, account_groups in fund_groups.items():
                if fund_key != 'no_fund':
                    fund = self.env['account.analytic.account'].browse(fund_key)
                    fund_node = {
                        "type": "fund",
                        "id": f"fund_{fund.id}",
                        "name": fund.name,
                        "code": fund.code,
                        "children": [],
                        "total_amount": 0,
                    }
                else:
                    fund_node = {
                        "type": "fund",
                        "id": "fund_no_fund",
                        "name": "ไม่ระบุกองทุน",
                        "code": "",
                        "children": [],
                        "total_amount": 0,
                    }
                
                # Build account level
                for account_key, line_data in account_groups.items():
                    if account_key != 'no_account':
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
                    for line_info in line_data:
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
                
                activity_node["children"].append(fund_node)
                activity_node["total_amount"] += fund_node["total_amount"]
            
            hierarchy.append(activity_node)
        
        # Sort hierarchy by activity code
        hierarchy.sort(key=lambda x: x.get('code', ''))
        
        return hierarchy

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