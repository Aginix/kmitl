from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetDashboard(TransactionCase):
    """Aggregation + parent_path roll-up for budget.dashboard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-DASH",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.parent = BA.create(
            {
                "code": "DASH00",
                "name": "Dashboard Parent",
                "budget_type": "expense",
                "budgetable": False,
            }
        )
        cls.child = BA.create(
            {
                "code": "DASH01",
                "name": "Dashboard Child",
                "budget_type": "expense",
                "budgetable": True,
                "parent_id": cls.parent.id,
            }
        )

    # --- helpers ---

    def _post_appropriation(self, account, amount, appropriation_type="initial"):
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": appropriation_type,
                "account_fiscal_year_id": self.fy.id,
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

    def _rows(self):
        data = self.env["budget.dashboard"].get_dashboard_data(
            self.fy.id, self.parent.id
        )
        return {row["id"]: row for row in data["rows"]}

    # --- tests ---

    def test_initial_current_and_adjustment_rollup(self):
        """initial / current / adjustment compute and roll up to the parent."""
        self._post_appropriation(self.child, 100_000, "initial")
        self._post_appropriation(self.child, 20_000, "supplementary")
        rows = self._rows()
        child, parent = rows[self.child.id], rows[self.parent.id]
        self.assertEqual(child["initial"], 100_000)
        self.assertEqual(child["current"], 120_000)
        self.assertEqual(child["adjustment"], 20_000)
        # pure roll-up: parent mirrors the only child
        self.assertEqual(parent["initial"], 100_000)
        self.assertEqual(parent["current"], 120_000)
        self.assertEqual(parent["remaining"], 120_000)
        self.assertEqual(parent["level"], 0)
        self.assertEqual(child["level"], 1)
        self.assertTrue(parent["has_children"])

    def test_commitment_breakdown_and_remaining(self):
        """b/c/d/e and remaining follow the net pipeline and roll up."""
        self._post_appropriation(self.child, 100_000, "initial")
        commitment = self._reserve(self.child, 60_000)
        self._add_line(commitment, "obligate", 40_000)
        self._add_line(commitment, "consume", 25_000)
        rows = self._rows()
        child = rows[self.child.id]
        self.assertEqual(child["cap"], 60_000)  # (3)
        self.assertEqual(child["reserved"], 20_000)  # b = 60 - 40
        self.assertEqual(child["obligated"], 15_000)  # c = 40 - 25
        self.assertEqual(child["consumed"], 25_000)  # d
        self.assertEqual(child["used"], 60_000)  # e = b + c + d
        self.assertEqual(child["remaining"], 40_000)  # f = 100 - 60
        parent = rows[self.parent.id]
        self.assertEqual(parent["used"], 60_000)
        self.assertEqual(parent["remaining"], 40_000)

    def test_consume_move_not_counted_as_budget(self):
        """The auto-created consume budget.move must not inflate current/initial."""
        self._post_appropriation(self.child, 100_000, "initial")
        commitment = self._reserve(self.child, 50_000)
        self._add_line(commitment, "obligate", 50_000)
        self._add_line(commitment, "consume", 50_000)
        child = self._rows()[self.child.id]
        self.assertEqual(child["current"], 100_000)  # consume move excluded
        self.assertEqual(child["initial"], 100_000)

    def _reserve_with_dist(self, account, amount, dist):
        commitment = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "account_id": account.id,
                "amount": amount,
                "analytic_distribution": dist,
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
                            "analytic_distribution": dist,
                        }
                    )
                ],
            }
        )
        commitment.action_reserve()
        return commitment

    def test_fund_filter_applies_to_commitment_columns(self):
        """A fund filter must narrow the commitment columns (cap/used), not only
        the move-sourced ones — guards against silently-dropped non-stored dims."""
        AA = self.env["account.analytic.account"]
        Plan = self.env["account.analytic.plan"]
        fund_plan = Plan.search([("code", "=", "funds")], limit=1) or Plan.create(
            {"name": "Funds", "code": "funds"}
        )
        fund_a = AA.create(
            {"name": "Fund A", "code": "DASH_FUNDA", "plan_id": fund_plan.id}
        )
        fund_b = AA.create(
            {"name": "Fund B", "code": "DASH_FUNDB", "plan_id": fund_plan.id}
        )
        self._post_appropriation(self.child, 100_000, "initial")
        self._reserve_with_dist(self.child, 30_000, {str(fund_a.id): 100.0})
        self._reserve_with_dist(self.child, 20_000, {str(fund_b.id): 100.0})
        data = self.env["budget.dashboard"].get_dashboard_data(
            self.fy.id, self.parent.id, {"fund_analytic_id": fund_a.id}
        )
        child = {r["id"]: r for r in data["rows"]}[self.child.id]
        self.assertEqual(child["cap"], 30_000)  # only Fund A commitment
        self.assertEqual(child["used"], 30_000)  # only Fund A reserve
