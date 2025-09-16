# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationF5Expense(models.AbstractModel):
    _name = "budget.appropriation.f5.expense"
    _description = "Budget Appropriation F5 Expense Report"

    @api.model
    def get_data(self, filters=None):
        """Get F5 expense report data with hierarchical structure"""
        if filters is None:
            filters = {}
        
        # Get filter values
        fiscal_year_id = filters.get("fiscal_year_id")
        department_ids = filters.get("department_ids", [])
        source_analytic_id = filters.get("source_analytic_id")
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        
        # Get or default fiscal year
        if fiscal_year_id:
            fiscal_year = self.env["account.fiscal.year"].browse(fiscal_year_id)
        else:
            fiscal_year = self.env["account.fiscal.year"].search(
                [], limit=1, order="date_from DESC"
            )
            if not fiscal_year:
                raise UserError(_("No fiscal year found"))
        
        # Get or default source analytic
        if source_analytic_id:
            source_analytic = self.env["account.analytic.account"].browse(source_analytic_id)
        else:
            # Default to government budget source (source code "1")
            source_analytic = self.env["account.analytic.account"].search([
                ("root_plan_id.code", "=", "sources"),
                ("code", "=", "1")
            ], limit=1)
            if not source_analytic:
                raise UserError(_("Default source analytic account not found"))
        
        # Use fiscal year dates if specific dates not provided
        if not date_from:
            date_from = fiscal_year.date_from
        if not date_to:
            date_to = fiscal_year.date_to
        
        # Build domain for appropriation lines
        appropriation_domain = [
            ("appropriation_id.budget_type", "=", "expense"),
            ("appropriation_id.state", "=", "posted"),
            ("appropriation_id.date_range_fy_id", "=", fiscal_year.id),
            ("appropriation_id.source_analytic_id", "=", source_analytic.id),
        ]
        
        # Add date filters
        if date_from:
            appropriation_domain.append(("appropriation_id.date", ">=", date_from))
        if date_to:
            appropriation_domain.append(("appropriation_id.date", "<=", date_to))
        
        # Add department filter
        if department_ids:
            all_dept_ids = self._get_department_with_children(department_ids)
            appropriation_domain.append(("appropriation_id.department_analytic_id", "in", all_dept_ids))
        
        # Get appropriation lines
        appropriation_lines = self.env["budget.appropriation.line"].search(appropriation_domain)
        
        # Build hierarchical tree
        hierarchy = self._build_hierarchy(appropriation_lines)
        
        # Calculate summary data
        total_amount = sum(line.balance for line in appropriation_lines)
        total_lines = len(appropriation_lines)
        activities_count = len(hierarchy)
        
        return {
            "hierarchy": hierarchy,
            "summary": {
                "total_amount": total_amount,
                "total_lines": total_lines,
                "activities_count": activities_count,
            },
            "filters": {
                "fiscal_year": {
                    "id": fiscal_year.id,
                    "name": fiscal_year.name,
                    "date_from": fiscal_year.date_from.strftime("%Y-%m-%d"),
                    "date_to": fiscal_year.date_to.strftime("%Y-%m-%d"),
                },
                "source_analytic": {
                    "id": source_analytic.id,
                    "code": source_analytic.code,
                    "name": source_analytic.name,
                },
                "departments": self._get_selected_departments(department_ids) if department_ids else None,
                "date_from": date_from.strftime("%Y-%m-%d") if date_from else None,
                "date_to": date_to.strftime("%Y-%m-%d") if date_to else None,
            },
            "current_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    
    @api.model
    def get_filter_options(self):
        """Get available filter options"""
        fiscal_years = self.env["account.fiscal.year"].search([], order="date_from DESC")
        departments = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "departments")
        ], order="code")
        sources = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "sources")
        ], order="code")
        
        return {
            "fiscal_years": [{
                "id": fy.id,
                "name": fy.name,
                "date_from": fy.date_from.strftime("%Y-%m-%d"),
                "date_to": fy.date_to.strftime("%Y-%m-%d"),
            } for fy in fiscal_years],
            "departments": self._build_department_hierarchy(),
            "sources": [{
                "id": source.id,
                "code": source.code,
                "name": source.name,
            } for source in sources],
        }
    
    def _build_hierarchy(self, appropriation_lines):
        """Build hierarchical tree: Activity → Fund → Budget Account → Lines"""
        if not appropriation_lines:
            return []
        
        hierarchy = {}
        
        for line in appropriation_lines:
            # Get dimensions
            activity = line.activity_analytic_id
            fund = line.fund_analytic_id
            account = line.budget_account_id
            
            # Build hierarchy path
            activity_key = f"activity_{activity.id}" if activity else "activity_none"
            fund_key = f"fund_{fund.id}" if fund else "fund_none"
            account_key = f"account_{account.id}" if account else "account_none"
            
            # Initialize activity level
            if activity_key not in hierarchy:
                hierarchy[activity_key] = {
                    "key": activity_key,
                    "type": "activity",
                    "id": activity.id if activity else None,
                    "code": activity.code if activity else "",
                    "name": activity.name if activity else _("No Activity"),
                    "complete_name": self._get_complete_name_without_codes(activity) if activity else _("No Activity"),
                    "amount": 0.0,
                    "total_amount": 0.0,
                    "level": 0,
                    "children": {},
                    "line_details": [],
                }
            
            # Initialize fund level
            if fund_key not in hierarchy[activity_key]["children"]:
                hierarchy[activity_key]["children"][fund_key] = {
                    "key": f"{activity_key}_{fund_key}",
                    "type": "fund",
                    "id": fund.id if fund else None,
                    "code": fund.code if fund else "",
                    "name": fund.name if fund else _("No Fund"),
                    "complete_name": self._get_complete_name_without_codes(fund) if fund else _("No Fund"),
                    "amount": 0.0,
                    "total_amount": 0.0,
                    "level": 1,
                    "children": {},
                    "line_details": [],
                }
            
            # Initialize account level
            if account_key not in hierarchy[activity_key]["children"][fund_key]["children"]:
                hierarchy[activity_key]["children"][fund_key]["children"][account_key] = {
                    "key": f"{activity_key}_{fund_key}_{account_key}",
                    "type": "account",
                    "id": account.id if account else None,
                    "code": account.code if account else "",
                    "name": account.name if account else _("No Account"),
                    "complete_name": account.name if account else _("No Account"),
                    "amount": 0.0,
                    "total_amount": 0.0,
                    "level": 2,
                    "children": [],
                    "line_details": [],
                }
            
            # Add line details to account
            account_node = hierarchy[activity_key]["children"][fund_key]["children"][account_key]
            line_data = {
                "id": line.id,
                "name": line.name or _("Appropriation Line"),
                "amount": line.balance,
                "appropriation_name": line.appropriation_id.name,
                "appropriation_date": line.appropriation_id.date.strftime("%d/%m/%Y") if line.appropriation_id.date else "",
            }
            account_node["line_details"].append(line_data)
            account_node["amount"] += line.balance
            
            # Update parent amounts
            hierarchy[activity_key]["children"][fund_key]["amount"] += line.balance
            hierarchy[activity_key]["amount"] += line.balance
        
        # Convert to list format and calculate totals
        result = []
        for activity_node in hierarchy.values():
            # Convert fund children
            fund_children = []
            for fund_node in activity_node["children"].values():
                # Convert account children
                account_children = []
                for account_node in fund_node["children"].values():
                    account_node["total_amount"] = account_node["amount"]
                    account_children.append(account_node)
                
                fund_node["children"] = sorted(account_children, key=lambda x: x["code"])
                fund_node["total_amount"] = fund_node["amount"]
                fund_children.append(fund_node)
            
            activity_node["children"] = sorted(fund_children, key=lambda x: x["code"])
            activity_node["total_amount"] = activity_node["amount"]
            result.append(activity_node)
        
        # Sort activities by code
        return sorted(result, key=lambda x: x["code"])
    
    def _get_department_with_children(self, department_ids):
        """Get department IDs including all children"""
        if not department_ids:
            return []
        
        departments = self.env["account.analytic.account"].browse(department_ids)
        all_dept_ids = list(department_ids)
        
        for dept in departments:
            children = self.env["account.analytic.account"].search([
                ("parent_path", "like", f"{dept.parent_path}%"),
                ("id", "!=", dept.id)
            ])
            all_dept_ids.extend(children.ids)
        
        return list(set(all_dept_ids))
    
    def _get_selected_departments(self, department_ids):
        """Get selected department details"""
        if not department_ids:
            return []
        
        departments = self.env["account.analytic.account"].browse(department_ids)
        return [{
            "id": dept.id,
            "code": dept.code,
            "name": dept.name,
            "complete_name": self._get_complete_name_without_codes(dept),
        } for dept in departments]
    
    def _build_department_hierarchy(self):
        """Build department hierarchy for filter display"""
        departments = self.env["account.analytic.account"].search([
            ("root_plan_id.code", "=", "departments"),
            ("parent_id", "=", False)  # Get root departments only
        ], order="code")
        
        def build_children(parent):
            children = self.env["account.analytic.account"].search([
                ("parent_id", "=", parent.id)
            ], order="code")
            
            result = []
            for child in children:
                child_data = {
                    "id": child.id,
                    "code": child.code,
                    "name": child.name,
                    "complete_name": self._get_complete_name_without_codes(child),
                    "children": build_children(child)
                }
                result.append(child_data)
            return result
        
        hierarchy = []
        for dept in departments:
            dept_data = {
                "id": dept.id,
                "code": dept.code,
                "name": dept.name,
                "complete_name": self._get_complete_name_without_codes(dept),
                "children": build_children(dept)
            }
            hierarchy.append(dept_data)
        
        return hierarchy
    
    def _get_complete_name_without_codes(self, record):
        """Get complete name without codes"""
        if not record:
            return ""
        
        if hasattr(record, 'complete_name') and record.complete_name:
            # Remove codes from complete_name
            import re
            return re.sub(r'\[.*?\]\s*', '', record.complete_name)
        return record.name