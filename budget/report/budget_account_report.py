from odoo import api, models


class BudgetAccountReport(models.AbstractModel):
    _name = "report.budget.report_budget_account"
    _description = "Budget Account Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        """
        Prepare data for the budget account report.
        Returns accounts sorted by:
        1. Budget type (Revenue first, then Expense)
        2. Hierarchy (parent before children)
        3. Code (alphabetically within same level)
        """
        docs = self.env["budget.account"].browse(docids) if docids else self.env["budget.account"].search([])
        
        # Get all budget accounts if no specific ones selected
        if not docs:
            docs = self.env["budget.account"].search([])
        
        # Separate revenue and expense accounts
        revenue_accounts = docs.filtered(lambda a: a.budget_type == "revenue")
        expense_accounts = docs.filtered(lambda a: a.budget_type == "expense")
        
        # Sort each group hierarchically
        sorted_revenue = self._sort_hierarchically(revenue_accounts)
        sorted_expense = self._sort_hierarchically(expense_accounts)
        
        return {
            "doc_ids": docids,
            "doc_model": "budget.account",
            "docs": docs,
            "revenue_accounts": sorted_revenue,
            "expense_accounts": sorted_expense,
            "company": self.env.company,
        }
    
    def _sort_hierarchically(self, accounts):
        """
        Sort accounts hierarchically maintaining parent-child relationships.
        Within same level, sort by code.
        """
        def get_sorted_tree(parent_accounts):
            result = []
            # Sort by code within same level
            for account in parent_accounts.sorted("code"):
                result.append(account)
                # Get children and sort them recursively
                children = accounts.filtered(lambda a: a.parent_id == account)
                if children:
                    result.extend(get_sorted_tree(children))
            return result
        
        # Start with root accounts (no parent)
        root_accounts = accounts.filtered(lambda a: not a.parent_id)
        return get_sorted_tree(root_accounts)