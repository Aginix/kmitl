from datetime import date

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetController(TransactionCase):
    """Control-node availability engine (ADR 0005).

    Covers: exact-leaf availability, coarse/ancestor coverage with a shared
    pool (the personnel-budget case), sibling no-double-count, the un-floored
    negative result, and per-dimension matching incl. the cross-dimension guard.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
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
        # Coarse pool: appropriation lands on the parent, leaves are empty.
        cls.coarse = BA.create(
            {"code": "CTRL_P", "name": "Coarse Parent", "budget_type": "expense"}
        )
        cls.child_a = BA.create(
            {
                "code": "CTRL_A",
                "name": "Child A",
                "budget_type": "expense",
                "parent_id": cls.coarse.id,
            }
        )
        cls.child_b = BA.create(
            {
                "code": "CTRL_B",
                "name": "Child B",
                "budget_type": "expense",
                "parent_id": cls.coarse.id,
            }
        )
        # Standalone leaves with their own appropriation.
        cls.leaf = BA.create(
            {"code": "CTRL_L", "name": "Leaf", "budget_type": "expense"}
        )
        cls.leaf2 = BA.create(
            {"code": "CTRL_L2", "name": "Leaf 2", "budget_type": "expense"}
        )
        cls.dimleaf = BA.create(
            {"code": "CTRL_D", "name": "Dim Leaf", "budget_type": "expense"}
        )

        Plan = env["account.analytic.plan"]
        fund_plan = Plan.search([("code", "=", "funds")], limit=1) or Plan.create(
            {"name": "Funds", "code": "funds"}
        )
        AA = env["account.analytic.account"]
        cls.fund_a = AA.create(
            {"name": "Fund A", "code": "CTRL_FA", "plan_id": fund_plan.id}
        )
        cls.fund_b = AA.create(
            {"name": "Fund B", "code": "CTRL_FB", "plan_id": fund_plan.id}
        )
        cls.controller = env["budget.controller"]

    # --- helpers ---

    def _appropriate(self, account, amount, fund=None):
        line_vals = {"account_id": account.id, "balance": amount}
        if fund:
            line_vals["fund_analytic_id"] = fund.id
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "line_ids": [Command.create(line_vals)],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _reserve(self, account, amount, dist=None):
        commitment = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "account_id": account.id,
                "amount": amount,
                "analytic_distribution": dist or False,
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
                            "analytic_distribution": dist or False,
                        }
                    )
                ],
            }
        )
        commitment.action_reserve()
        return commitment

    def _available(self, account, dist=None):
        return self.controller.get_available(account.id, dist or {}, self.fy.id)

    # --- tests ---

    def test_exact_leaf_availability(self):
        """Appropriation and reservation at the same leaf: current − used."""
        self._appropriate(self.leaf, 100_000)
        self._reserve(self.leaf, 60_000)
        self.assertEqual(self._available(self.leaf), 40_000)

    def test_unfunded_is_zero(self):
        """A leaf with no appropriation and no usage has zero available."""
        self.assertEqual(self._available(self.child_a), 0.0)

    def test_coarse_ancestor_coverage_shared_pool(self):
        """Appropriation at the parent covers child reservations from one pool.

        Both children draw the *same* pool, so a reservation on one decrements
        what the sibling sees — no double-counting (ADR 0005, Case A / P2).
        """
        self._appropriate(self.coarse, 100_000)
        # child sees the ancestor's pool even with no appropriation of its own
        self.assertEqual(self._available(self.child_a), 100_000)
        self._reserve(self.child_a, 60_000)
        self.assertEqual(self._available(self.child_a), 40_000)
        # sibling sees the shared pool already drawn down to 40k
        self.assertEqual(self._available(self.child_b), 40_000)

    def test_not_floored_can_go_negative(self):
        """Over-committed combinations report a negative available (no floor)."""
        self._appropriate(self.leaf2, 50_000)
        self._reserve(self.leaf2, 80_000)  # cap 80k, reserve 80k > pool
        self.assertEqual(self._available(self.leaf2), -30_000)

    def test_dimension_match_and_cross_dimension_guard(self):
        """Availability is per (account × dimension); unused dims must be empty."""
        self._appropriate(self.dimleaf, 100_000, fund=self.fund_a)
        # same fund -> full pool
        self.assertEqual(
            self._available(self.dimleaf, {str(self.fund_a.id): 100.0}), 100_000
        )
        # different fund -> unfunded
        self.assertEqual(
            self._available(self.dimleaf, {str(self.fund_b.id): 100.0}), 0.0
        )
        # no fund specified must NOT leak the fund-A appropriation
        self.assertEqual(self._available(self.dimleaf, {}), 0.0)

    def _reserve_multi(self, account_amounts):
        first = account_amounts[0][0]
        return self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "account_id": first.id,
                "amount": sum(amt for _, amt in account_amounts),
                "account_fiscal_year_id": self.fy.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "move_type": "reserve",
                            "account_id": account.id,
                            "amount": amt,
                            "name": "Reserve",
                        }
                    )
                    for account, amt in account_amounts
                ],
            }
        )

    def test_cross_charge_requires_flag(self):
        """Multiple budget codes in one reservation need cross_chargeable=True."""
        with self.assertRaises(ValidationError):
            self._reserve_multi([(self.child_a, 10_000), (self.child_b, 10_000)])
        (self.child_a | self.child_b).write({"cross_chargeable": True})
        commitment = self._reserve_multi(
            [(self.child_a, 10_000), (self.child_b, 10_000)]
        )
        self.assertEqual(len(commitment.line_ids), 2)

    def test_reservation_grid_reuses_dashboard_columns_and_flags_selectable(self):
        """The picker feed = dashboard columns + budgetable/selectable flags."""
        self._appropriate(self.leaf, 100_000)
        self._reserve(self.leaf, 60_000)
        grid = self.env["budget.dashboard"].get_reservation_grid(
            self.fy.id, {}, root_account_id=self.leaf.id
        )
        leaf = {r["id"]: r for r in grid["rows"]}[self.leaf.id]
        # full dashboard columns are present and correct
        self.assertEqual(leaf["current"], 100_000)
        self.assertEqual(leaf["used"], 60_000)
        self.assertEqual(leaf["remaining"], 40_000)
        # no account_domain -> selectable mirrors budgetable
        self.assertTrue(leaf["budgetable"])
        self.assertTrue(leaf["selectable"])
        # account_domain narrows selectable
        grid2 = self.env["budget.dashboard"].get_reservation_grid(
            self.fy.id,
            {},
            root_account_id=self.leaf.id,
            account_domain=[("id", "=", self.leaf2.id)],
        )
        leaf2row = {r["id"]: r for r in grid2["rows"]}[self.leaf.id]
        self.assertFalse(leaf2row["selectable"])
