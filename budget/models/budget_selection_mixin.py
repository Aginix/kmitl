from odoo import models


class BudgetSelectionMixin(models.AbstractModel):
    _name = "budget.selection.mixin"
    _description = "Budget Selection Mixin"

    def action_select_budget(self):
        self.ensure_one()
        ctx = {
            "default_res_model": self._name,
            "default_res_id": self.id,
        }
        fields = self._fields
        if "budget_account_id" in fields and self.budget_account_id:
            ctx["default_budget_account_id"] = self.budget_account_id.id
        if "activity_analytic_id" in fields and self.activity_analytic_id:
            ctx["default_activity_analytic_id"] = self.activity_analytic_id.id
        if "department_analytic_id" in fields and self.department_analytic_id:
            ctx["default_department_analytic_id"] = self.department_analytic_id.id
        if "fund_analytic_id" in fields and self.fund_analytic_id:
            ctx["default_fund_analytic_id"] = self.fund_analytic_id.id
        if "source_analytic_id" in fields and self.source_analytic_id:
            ctx["default_source_analytic_id"] = self.source_analytic_id.id
        return {
            "type": "ir.actions.act_window",
            "name": "เลือกงบประมาณ",
            "res_model": "budget.selection.wizard",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }
