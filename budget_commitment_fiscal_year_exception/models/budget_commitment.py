from odoo import api, fields, models
from odoo.modules import module as odoo_module


class BudgetCommitment(models.Model):
    _name = "budget.commitment"
    _inherit = ["budget.commitment", "base.exception"]
    # Keep the commitment's own ordering — mixing in base.exception would
    # otherwise pull its "main_exception_id asc" _order.
    _order = "date desc, name desc, id desc"

    @api.model
    def _reverse_field(self):
        return "budget_commitment_ids"

    def _exception_fiscal_year_not_current(self):
        """True when the ปีงบประมาณ being reserved is not the current one (the
        year whose date range covers today)."""
        self.ensure_one()
        # Existing suites hard-code a past ปีงบ, so the rule is off while tests run;
        # only this module's own tests opt back in via the context key.
        if odoo_module.current_test and not self.env.context.get(
            "test_fiscal_year_exception"
        ):
            return False
        if self.state not in ("draft",):
            return False
        fy = self.account_fiscal_year_id
        today = fields.Date.context_today(self)
        return not fy or not (fy.date_from <= today <= fy.date_to)

    def action_reserve(self):
        # Raises instead of returning a popup: hosts (kmitl_project,
        # procurement_plan_budget, the budget mixins, budget.controller) reserve
        # programmatically and would silently skip the reserve on a popup return.
        self._check_exception()
        return super().action_reserve()
