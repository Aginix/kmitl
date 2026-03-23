from odoo import models


class BudgetExceptionMixin(models.AbstractModel):
    _name = "budget.exception.mixin"
    _description = "Budget Exception Mixin"

    def _get_budget_account(self):
        """Return budget.account record for validation.
        Override in models where the field name differs."""
        if "budget_account_id" in self._fields:
            return self.budget_account_id
        if "account_id" in self._fields:
            return self.account_id
        return self.env["budget.account"]

    def _has_5_digit_budget_code(self):
        """Return True if budget account code is exactly 5 digits (parent-level only)."""
        account = self._get_budget_account()
        return bool(account and len(account.code or "") == 5)
