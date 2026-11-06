from datetime import date, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

CTX = {"test_fiscal_year_exception": True}


def _current_fy(env):
    today = date.today()
    return env["account.fiscal.year"].search(
        [("date_from", "<=", today), ("date_to", ">=", today)], limit=1
    ) or env["account.fiscal.year"].create(
        {
            "name": "FY-CURRENT-EXC",
            "date_from": today - timedelta(days=100),
            "date_to": today + timedelta(days=100),
            "company_id": env.company.id,
        }
    )


def _past_fy(env):
    return env["account.fiscal.year"].create(
        {
            "name": "FY-PAST-EXC",
            "date_from": date(2001, 10, 1),
            "date_to": date(2002, 9, 30),
            "company_id": env.company.id,
        }
    )


@tagged("post_install", "-at_install")
class TestBudgetCommitmentFiscalYearException(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.current_fy = _current_fy(env)
        cls.past_fy = _past_fy(env)
        cls.Model = env["budget.commitment"].with_context(**CTX)
        # kmitl_demo sets this to True; pin it so availability never interferes.
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", True)
        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]
        dists = {}
        for code in ("departments", "sources", "activities", "funds"):
            plan = Plan.search([("code", "=", code)], limit=1) or Plan.create(
                {"name": code, "code": code}
            )
            dists[
                str(
                    AA.create(
                        {"name": code, "code": "FYX_" + code, "plan_id": plan.id}
                    ).id
                )
            ] = 100.0
        cls.dist = dists
        cls.account = env["budget.account"].create(
            {
                "code": "FYX001",
                "name": "FYX",
                "budget_type": "expense",
                "budgetable": True,
            }
        )

    def _commitment(self, fy):
        return self.Model.create(
            {
                "date": date.today(),
                "title": "FY exception",
                "account_id": self.account.id,
                "amount": 1000,
                "analytic_distribution": self.dist,
                "account_fiscal_year_id": fy.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
            }
        )

    def test_helper(self):
        self.assertTrue(
            self._commitment(self.past_fy)._exception_fiscal_year_not_current()
        )
        c = self._commitment(self.current_fy)
        self.assertFalse(c._exception_fiscal_year_not_current())
        c.state = "reserved"
        self.assertFalse(c._exception_fiscal_year_not_current())

    def test_test_mode_bypass_without_context(self):
        c = self._commitment(self.past_fy).with_context(
            test_fiscal_year_exception=False
        )
        self.assertFalse(c._exception_fiscal_year_not_current())

    def test_reserve_past_year_raises(self):
        with self.assertRaises(ValidationError):
            self._commitment(self.past_fy).action_reserve()

    def test_reserve_current_year(self):
        c = self._commitment(self.current_fy)
        c.action_reserve()
        self.assertEqual(c.state, "reserved")
