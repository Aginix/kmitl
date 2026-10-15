from datetime import date

from odoo import Command
from odoo.exceptions import UserError, ValidationError
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
        # Hierarchical activity tree (ADR-0016 descendant draw): main → sub → leaf,
        # plus a sibling of sub. Needs account_analytic_parent (parent_id).
        cls.has_analytic_tree = "parent_id" in AA._fields
        act_plan = Plan.search(
            [("code", "=", "activities")], limit=1
        ) or Plan.create({"name": "Activities", "code": "activities"})
        cls.act_main = AA.create(
            {"name": "Act Main", "code": "CTRL_ACT_M", "plan_id": act_plan.id}
        )
        sub_vals = {"name": "Act Sub", "code": "CTRL_ACT_S", "plan_id": act_plan.id}
        sib_vals = {"name": "Act Sib", "code": "CTRL_ACT_X", "plan_id": act_plan.id}
        if cls.has_analytic_tree:
            sub_vals["parent_id"] = cls.act_main.id
            sib_vals["parent_id"] = cls.act_main.id
        cls.act_sub = AA.create(sub_vals)
        cls.act_sib = AA.create(sib_vals)
        leaf_vals = {
            "name": "Act Leaf",
            "code": "CTRL_ACT_L",
            "plan_id": act_plan.id,
        }
        if cls.has_analytic_tree:
            leaf_vals["parent_id"] = cls.act_sub.id
        cls.act_leaf = AA.create(leaf_vals)
        cls.controller = env["budget.controller"]

    # --- helpers ---

    def _appropriate(self, account, amount, fund=None, **cols):
        line_vals = {"account_id": account.id, "balance": amount}
        if fund:
            line_vals["fund_analytic_id"] = fund.id
        for column, rec in cols.items():
            line_vals[column] = rec.id if rec else False
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
                "title": "Test commitment",
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

    def test_floating_pool_counts_tagged_owner_reserves(self):
        """A floating-pool check (no ownership tag) must count a reserve that
        DOES carry one (a project's reserve).

        Project appropriation is untagged (kmitl_project absent); a project's
        reserve carries its kmitl_project tag. If the tagged reserve were
        excluded from ``used``, every project would see the full pool and could
        over-reserve it (ADR-0007). Here 100k pool − a 60k tagged reserve = 40k.
        """
        Plan = self.env["account.analytic.plan"]
        proj_plan = Plan.search(
            [("code", "=", "kmitl_project")], limit=1
        ) or Plan.create({"name": "Project", "code": "kmitl_project"})
        project = self.env["account.analytic.account"].create(
            {"name": "Proj X", "code": "CTRL_PRJ", "plan_id": proj_plan.id}
        )
        self._appropriate(self.dimleaf, 100_000, fund=self.fund_a)
        self._reserve(
            self.dimleaf,
            60_000,
            dist={str(self.fund_a.id): 100.0, str(project.id): 100.0},
        )
        # the 4D floating check (fund only, no kmitl_project) still sees the
        # tagged reserve as used
        self.assertEqual(
            self._available(self.dimleaf, {str(self.fund_a.id): 100.0}), 40_000
        )

    def _reserve_multi(self, account_amounts):
        first = account_amounts[0][0]
        return self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Test commitment",
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

    # --- ADR-0016: reserve at a descendant of the funded code ---

    def _enforce_availability_check(self):
        """kmitl_demo turns on ``budget.allow_negative`` in the post_install DB,
        which short-circuits the reserve check. Clear it so the check enforces."""
        self.env["ir.config_parameter"].sudo().set_param(
            "budget.allow_negative", False
        )

    def _reserve_dim(self, account, amount, dist):
        """Reserve with a header + line distribution (dims live in both)."""
        commitment = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Test commitment",
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

    def test_descendant_activity_draws_parent_pool(self):
        """A pool funded at กิจกรรมหลัก is drawable at a descendant กิจกรรมย่อย."""
        if not self.has_analytic_tree:
            self.skipTest("analytic hierarchy (account_analytic_parent) absent")
        self._appropriate(
            self.dimleaf, 100_000, activity_analytic_id=self.act_main
        )
        sub = {str(self.act_sub.id): 100.0}
        leaf = {str(self.act_leaf.id): 100.0}
        # a descendant sees the parent pool
        self.assertEqual(self._available(self.dimleaf, sub), 100_000)
        self.assertEqual(self._available(self.dimleaf, leaf), 100_000)
        # reserving at the descendant decrements what a sibling sees
        self._reserve_dim(self.dimleaf, 60_000, leaf)
        self.assertEqual(self._available(self.dimleaf, leaf), 40_000)
        self.assertEqual(
            self._available(self.dimleaf, {str(self.act_sib.id): 100.0}), 40_000
        )

    def test_descendants_on_every_axis_at_once(self):
        """Account + activity + fund all resolve to one covering pool."""
        if not self.has_analytic_tree:
            self.skipTest("analytic hierarchy (account_analytic_parent) absent")
        self._appropriate(
            self.coarse,
            100_000,
            activity_analytic_id=self.act_main,
            fund=self.fund_a,
        )
        dist = {
            str(self.act_leaf.id): 100.0,
            str(self.fund_a.id): 100.0,
        }
        # child account + descendant activity + same fund draws the one pool
        self.assertEqual(self._available(self.child_a, dist), 100_000)

    def test_h1_no_downward_leak(self):
        """A pool at a child does NOT back a reservation at the parent code.

        Pre-fix, a bare parent node defaulted to itself and swept in every pool
        below it (double-spend). Now the parent is uncovered → 0 available and
        reserving there raises (ADR-0016, H1).
        """
        if not self.has_analytic_tree:
            self.skipTest("analytic hierarchy (account_analytic_parent) absent")
        self._enforce_availability_check()
        self._appropriate(
            self.dimleaf, 100_000, activity_analytic_id=self.act_leaf
        )
        # the ancestor activity is NOT funded at/above -> uncovered
        self.assertEqual(
            self._available(self.dimleaf, {str(self.act_main.id): 100.0}), 0.0
        )
        with self.assertRaises(UserError):
            self._reserve_dim(
                self.dimleaf, 10_000, {str(self.act_main.id): 100.0}
            )

    def test_zero_line_is_not_a_pool(self):
        """A net-zero appropriation coordinate does not fund a reservation."""
        self._appropriate(self.leaf, 0.0)
        self.assertEqual(self._available(self.leaf), 0.0)

    def test_h2_two_lines_under_one_pool(self):
        """Two reserve lines resolving to one pool are checked together (H2)."""
        if not self.has_analytic_tree:
            self.skipTest("analytic hierarchy (account_analytic_parent) absent")
        self._enforce_availability_check()
        (self.child_a | self.child_b).write({"cross_chargeable": True})
        self._appropriate(
            self.coarse, 100_000, activity_analytic_id=self.act_main
        )
        leaf = {str(self.act_leaf.id): 100.0}
        # both lines resolve to the coarse/act_main pool; 70k + 70k > 100k
        commitment = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Two lines one pool",
                "account_id": self.child_a.id,
                "amount": 140_000,
                "analytic_distribution": leaf,
                "account_fiscal_year_id": self.fy.id,
                "company_id": self.env.company.id,
                "currency_id": self.env.company.currency_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "move_type": "reserve",
                            "account_id": self.child_a.id,
                            "amount": 70_000,
                            "name": "R1",
                            "analytic_distribution": leaf,
                        }
                    ),
                    Command.create(
                        {
                            "move_type": "reserve",
                            "account_id": self.child_b.id,
                            "amount": 70_000,
                            "name": "R2",
                            "analytic_distribution": leaf,
                        }
                    ),
                ],
            }
        )
        with self.assertRaises(UserError):
            commitment.action_reserve()

    def test_get_available_detail_returns_pool(self):
        """get_available_detail names the covering control node for the picker."""
        if not self.has_analytic_tree:
            self.skipTest("analytic hierarchy (account_analytic_parent) absent")
        self._appropriate(
            self.dimleaf, 100_000, activity_analytic_id=self.act_main
        )
        detail = self.controller.get_available_detail(
            self.dimleaf.id, {str(self.act_leaf.id): 100.0}, self.fy.id
        )
        self.assertEqual(detail["available"], 100_000)
        self.assertTrue(detail["pool"])
        self.assertEqual(detail["pool"]["account"]["id"], self.dimleaf.id)
        self.assertEqual(
            detail["pool"]["dims"]["activity_analytic_id"]["id"], self.act_main.id
        )
        # uncovered -> no pool, zero available
        empty = self.controller.get_available_detail(
            self.child_a.id, {str(self.act_leaf.id): 100.0}, self.fy.id
        )
        self.assertIsNone(empty["pool"])
        self.assertEqual(empty["available"], 0.0)
