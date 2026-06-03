from datetime import date

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetController(TransactionCase):
    """get_budget_card payload + analytic-distribution bucketing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.controller = env["budget.controller"]
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-CTRL",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.account = BA.create(
            {
                "code": "CTRL01",
                "name": "Controller Account",
                "budget_type": "expense",
                "budgetable": True,
            }
        )

    # --- helpers (mirror test_budget_dashboard) ---

    def _post_appropriation(self, account, amount, appropriation_type="initial", fy=None):
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": appropriation_type,
                "account_fiscal_year_id": (fy or self.fy).id,
                "line_ids": [
                    Command.create({"account_id": account.id, "balance": amount})
                ],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _reserve(self, account, amount):
        commitment = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "account_id": account.id,
                "amount": amount,
                "account_fiscal_year_id": self.fy.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "move_type": "reserve",
                            "account_id": account.id,
                            "amount": amount,
                            "name": "Reserve",
                        }
                    )
                ],
            }
        )
        commitment.action_reserve()
        return commitment

    def _add_line(self, commitment, move_type, amount):
        return self.env["budget.commitment.line"].create(
            {
                "commitment_id": commitment.id,
                "move_type": move_type,
                "account_id": commitment.account_id.id,
                "amount": amount,
                "name": move_type,
            }
        )

    # --- tests ---

    def test_get_budget_card_figures(self):
        """The six figures mirror budget.dashboard for the same combination."""
        self._post_appropriation(self.account, 100_000)
        commitment = self._reserve(self.account, 60_000)
        self._add_line(commitment, "obligate", 40_000)
        self._add_line(commitment, "consume", 25_000)

        card = self.controller.get_budget_card(self.fy.id, self.account.id, {})
        self.assertTrue(card["ready"])
        self.assertEqual(card["current"], 100_000)
        self.assertEqual(card["reserved"], 20_000)  # b = 60 - 40
        self.assertEqual(card["obligated"], 15_000)  # c = 40 - 25
        self.assertEqual(card["consumed"], 25_000)  # d
        self.assertEqual(card["used"], 60_000)  # e = b + c + d
        self.assertEqual(card["remaining"], 40_000)  # f = 100 - 60

    def test_get_budget_card_over_budget(self):
        """Reserving beyond the appropriation yields a negative remaining."""
        self._reserve(self.account, 60_000)  # no appropriation posted
        card = self.controller.get_budget_card(self.fy.id, self.account.id, {})
        self.assertTrue(card["ready"])
        self.assertEqual(card["current"], 0)
        self.assertEqual(card["used"], 60_000)
        self.assertEqual(card["remaining"], -60_000)

    def test_get_budget_card_no_account(self):
        """No budget account -> not ready, all figures zero."""
        card = self.controller.get_budget_card(self.fy.id, False, {})
        self.assertFalse(card["ready"])
        for key in ("current", "reserved", "obligated", "consumed", "used", "remaining"):
            self.assertEqual(card[key], 0.0)

    def test_get_budget_card_fiscal_year_fallback(self):
        """A falsy fiscal year falls back to the fiscal year covering today."""
        today = fields.Date.today()
        fy_today = self.env["account.fiscal.year"].search(
            [
                ("date_from", "<=", today),
                ("date_to", ">=", today),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        if not fy_today:
            self.skipTest("No fiscal year covers today")

        account = self.env["budget.account"].create(
            {
                "code": "CTRLFY",
                "name": "Fallback Account",
                "budget_type": "expense",
                "budgetable": True,
            }
        )
        self._post_appropriation(account, 70_000, fy=fy_today)

        explicit = self.controller.get_budget_card(fy_today.id, account.id, {})
        fallback = self.controller.get_budget_card(False, account.id, {})
        self.assertTrue(fallback["ready"])
        self.assertEqual(fallback["current"], 70_000)
        self.assertEqual(fallback, explicit)

    def test_distribution_to_analytic_data_buckets_by_root_plan(self):
        """Dimensions bucket by root_plan_id.code, even for sub-plan accounts."""
        AA = self.env["account.analytic.account"]
        Plan = self.env["account.analytic.plan"]
        funds_plan = Plan.search([("code", "=", "funds")], limit=1) or Plan.create(
            {"name": "Funds", "code": "funds"}
        )
        acts_plan = Plan.search(
            [("code", "=", "activities")], limit=1
        ) or Plan.create({"name": "Activities", "code": "activities"})
        # A nested fund sub-plan: its own code is NOT "funds", but its root is.
        funds_sub = Plan.create(
            {"name": "Funds Sub", "code": "BC_FUNDS_SUB", "parent_id": funds_plan.id}
        )
        fund = AA.create(
            {"name": "Fund X", "code": "BC_FUNDX", "plan_id": funds_sub.id}
        )
        activity = AA.create(
            {"name": "Activity Y", "code": "BC_ACTY", "plan_id": acts_plan.id}
        )
        self.assertEqual(fund.root_plan_id.code, "funds")
        self.assertNotEqual(fund.plan_id.code, "funds")

        data = self.controller._distribution_to_analytic_data(
            self.account.id, {str(fund.id): 100, str(activity.id): 100}
        )
        self.assertEqual(data["account_id"], self.account.id)
        self.assertEqual(data["fund_analytic_id"], fund.id)
        self.assertEqual(data["activity_analytic_id"], activity.id)
        self.assertFalse(data["department_analytic_id"])
        self.assertFalse(data["source_analytic_id"])
