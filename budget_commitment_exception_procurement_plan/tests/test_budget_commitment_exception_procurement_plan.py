from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetCommitmentExceptionProcurementPlan(TransactionCase):
    """จองงบ on a procurement-plan budget code requires its plan's tag."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-BCEXP",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        cls.proc_ba = env["budget.account"].create(
            {
                "code": "BCP_PROCBA",
                "name": "Procurement BA",
                "budget_type": "expense",
                "budgetable": True,
                "procurement_plan": True,
            }
        )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(code, plan_code):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_code, "code": plan_code}
            )
            return AA.create({"name": code, "code": code, "plan_id": plan.id})

        cls.dims = [
            acc("BCP_DEPT", "departments"),
            acc("BCP_SRC", "sources"),
            acc("BCP_ACT", "activities"),
            acc("BCP_FUND", "funds"),
        ]
        cls.proc_tag = acc("BCP_PROC", "procurement_plan")
        cls.rule = env.ref(
            "budget_commitment_exception_procurement_plan."
            "budget_commitment_excep_procurement_plan_tag"
        )

    def _commitment(self, tag=None):
        distribution = {str(a.id): 100.0 for a in self.dims}
        if tag:
            distribution[str(tag.id)] = 100.0
        return self.env["budget.commitment"].create(
            {
                "title": "Plan slip",
                "account_id": self.proc_ba.id,
                "amount": 1000,
                "analytic_distribution": distribution,
                "account_fiscal_year_id": self.fy.id,
            }
        )

    def test_plan_code_without_tag_is_blocked(self):
        c = self._commitment()
        with self.assertRaisesRegex(ValidationError, self.rule.name):
            c.action_reserve()
        self.assertEqual(c.state, "draft")

    def test_plan_code_with_tag_passes_rule(self):
        c = self._commitment(tag=self.proc_tag)
        self.assertFalse(c.detect_exceptions())

    def test_rule_switched_off(self):
        self.rule.active = False
        c = self._commitment()
        self.assertFalse(c.detect_exceptions())
