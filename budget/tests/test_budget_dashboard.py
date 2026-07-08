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

    def _post_appropriation_act(
        self, account, amount, activity, appropriation_type="initial"
    ):
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": appropriation_type,
                "account_fiscal_year_id": self.fy.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": account.id,
                            "balance": amount,
                            "analytic_distribution": {str(activity.id): 100.0},
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _breakdown(self):
        data = self.env["budget.dashboard"].get_dashboard_data(
            self.fy.id, self.parent.id, {}, "activity_analytic_id"
        )
        return {row["key"]: row for row in data["rows"]}

    def test_activity_breakdown_nests_accounts_and_rolls_up(self):
        """Activities form the outer tree; the budget-account subtree nests under
        the exact activity it's tagged to, and both trees roll up."""
        AA = self.env["account.analytic.account"]
        Plan = self.env["account.analytic.plan"]
        plan = Plan.search([("code", "=", "activities")], limit=1) or Plan.create(
            {"name": "Activities", "code": "activities"}
        )
        act_parent = AA.create(
            {"name": "Develop", "code": "ACT09", "plan_id": plan.id}
        )
        act_child = AA.create(
            {
                "name": "Higher Ed",
                "code": "ACT09007",
                "plan_id": plan.id,
                "parent_id": act_parent.id,
            }
        )
        self._post_appropriation_act(self.child, 100_000, act_child)
        self._reserve_with_dist(self.child, 60_000, {str(act_child.id): 100.0})

        rows = self._breakdown()
        p_key = "a%s" % act_parent.id
        c_key = "a%s" % act_child.id
        self.assertIn(p_key, rows)
        self.assertIn(c_key, rows)
        parent_act, child_act = rows[p_key], rows[c_key]
        # outer hierarchy: dimension rows, parent at level 0, child nested under it
        self.assertEqual(parent_act["row_type"], "dim")
        self.assertEqual(parent_act["level"], 0)
        self.assertEqual(parent_act["parent_key"], False)
        self.assertEqual(child_act["level"], 1)
        self.assertEqual(child_act["parent_key"], p_key)
        # activity rolls up over its subtree: here parent mirrors its only child
        self.assertEqual(parent_act["current"], 100_000)
        self.assertEqual(child_act["current"], 100_000)
        self.assertEqual(child_act["cap"], 60_000)
        self.assertEqual(child_act["used"], 60_000)
        self.assertEqual(child_act["remaining"], 40_000)

        # budget-account subtree nests under the EXACT activity (the child),
        # itself rolling up over the account tree.
        acc_root_key = "a%s|b%s" % (act_child.id, self.parent.id)
        acc_leaf_key = "a%s|b%s" % (act_child.id, self.child.id)
        self.assertIn(acc_root_key, rows)
        self.assertIn(acc_leaf_key, rows)
        self.assertEqual(rows[acc_root_key]["parent_key"], c_key)
        self.assertEqual(rows[acc_leaf_key]["parent_key"], acc_root_key)
        leaf = rows[acc_leaf_key]
        self.assertEqual(leaf["row_type"], "account")
        self.assertEqual(leaf["account_id"], self.child.id)
        self.assertEqual(leaf["dims"]["activity_analytic_id"], act_child.id)
        self.assertEqual(leaf["current"], 100_000)
        self.assertEqual(leaf["cap"], 60_000)
        self.assertEqual(leaf["remaining"], 40_000)
        # exact-activity rule: accounts are NOT nested under the ancestor activity
        self.assertNotIn("a%s|b%s" % (act_parent.id, self.child.id), rows)

    def test_activity_breakdown_untagged_bucket(self):
        """Lines with no activity fall into the sentinel root so totals still
        reconcile with the flat report."""
        self._post_appropriation(self.child, 50_000, "initial")
        rows = self._breakdown()
        self.assertIn("a0", rows)
        sentinel = rows["a0"]
        self.assertEqual(sentinel["row_type"], "dim")
        self.assertEqual(sentinel["dims"]["activity_analytic_id"], False)
        self.assertEqual(sentinel["current"], 50_000)
        # the account subtree still nests under the sentinel
        self.assertIn("a0|b%s" % self.child.id, rows)
        self.assertEqual(rows["a0|b%s" % self.child.id]["current"], 50_000)

    def test_two_dim_breakdown_activities_then_departments(self):
        """activities › departments › account: each level nests under the exact
        parent node, rolls up over its subtree, and keys are path-encoded."""
        AA = self.env["account.analytic.account"]
        Plan = self.env["account.analytic.plan"]
        act_plan = Plan.search([("code", "=", "activities")], limit=1) or Plan.create(
            {"name": "Activities", "code": "activities"}
        )
        dept_plan = Plan.search(
            [("code", "=", "departments")], limit=1
        ) or Plan.create({"name": "Departments", "code": "departments"})
        # The outer dimension (activities) has its own parent/child hierarchy,
        # so the test also covers intra-dimension nesting within the breakdown.
        act_parent = AA.create(
            {"name": "Act P", "code": "ACT2D", "plan_id": act_plan.id}
        )
        act = AA.create(
            {
                "name": "Act C",
                "code": "ACT2D07",
                "plan_id": act_plan.id,
                "parent_id": act_parent.id,
            }
        )
        dept = AA.create({"name": "Dept", "code": "DEP2D", "plan_id": dept_plan.id})

        # appropriation: activity on the line, department on the move header
        # (which propagates to the line, matching production data flow).
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": dept.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.child.id,
                            "balance": 100_000,
                            "analytic_distribution": {str(act.id): 100.0},
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()
        self._reserve_with_dist(
            self.child, 60_000, {str(act.id): 100.0, str(dept.id): 100.0}
        )

        data = self.env["budget.dashboard"].get_dashboard_data(
            self.fy.id,
            self.parent.id,
            {},
            ["activity_analytic_id", "department_analytic_id"],
        )
        rows = {r["key"]: r for r in data["rows"]}
        ap_key = "a%s" % act_parent.id
        a_key = "a%s" % act.id
        ad_key = "a%s|p%s" % (act.id, dept.id)
        acc_root = "a%s|p%s|b%s" % (act.id, dept.id, self.parent.id)
        acc_leaf = "a%s|p%s|b%s" % (act.id, dept.id, self.child.id)
        for key in (ap_key, a_key, ad_key, acc_root, acc_leaf):
            self.assertIn(key, rows)
        # nesting: act parent(0) › act child(1) › department(2) › acc root(3) › leaf(4)
        self.assertEqual(rows[ap_key]["row_type"], "dim")
        self.assertEqual(rows[ap_key]["dim_level"], 0)
        self.assertEqual(rows[ap_key]["level"], 0)
        self.assertEqual(rows[ap_key]["parent_key"], False)
        # intra-dimension hierarchy: the child activity nests under its parent
        self.assertEqual(rows[a_key]["dim_level"], 0)
        self.assertEqual(rows[a_key]["level"], 1)
        self.assertEqual(rows[a_key]["parent_key"], ap_key)
        # cross-dimension nesting at depth > 0: department under the child activity
        self.assertEqual(rows[ad_key]["dim_level"], 1)
        self.assertEqual(rows[ad_key]["level"], 2)
        self.assertEqual(rows[ad_key]["parent_key"], a_key)
        self.assertEqual(rows[acc_root]["level"], 3)
        self.assertEqual(rows[acc_root]["parent_key"], ad_key)
        self.assertEqual(rows[acc_leaf]["level"], 4)
        self.assertEqual(rows[acc_leaf]["parent_key"], acc_root)
        # each level rolls up the whole subtree (single path here)
        self.assertEqual(rows[ap_key]["current"], 100_000)
        self.assertEqual(rows[a_key]["current"], 100_000)
        self.assertEqual(rows[ad_key]["current"], 100_000)
        self.assertEqual(rows[acc_leaf]["current"], 100_000)
        # cap co-locates with reserved at the (activity, department) node
        self.assertEqual(rows[ad_key]["cap"], 60_000)
        self.assertEqual(rows[ad_key]["used"], 60_000)
        self.assertEqual(rows[acc_leaf]["cap"], 60_000)
        self.assertEqual(rows[acc_leaf]["remaining"], 40_000)
        # the account leaf carries the full dimension tuple
        self.assertEqual(rows[acc_leaf]["dims"]["activity_analytic_id"], act.id)
        self.assertEqual(rows[acc_leaf]["dims"]["department_analytic_id"], dept.id)

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

    def test_returned_column_releases_reserved(self):
        """(g) ส่งคืนเงินเหลือจ่าย = Σ คืนจอง; b/e drop, f rises, and it rolls up."""
        self._post_appropriation(self.child, 100_000, "initial")
        commitment = self._reserve(self.child, 60_000)
        self._add_line(commitment, "obligate", 50_000)
        self._add_line(commitment, "consume", 50_000)
        # Return the 10k leftover (คืนจอง): a negative reserve line, is_return.
        self.env["budget.commitment.line"].create(
            {
                "commitment_id": commitment.id,
                "move_type": "reserve",
                "is_return": True,
                "account_id": commitment.account_id.id,
                "amount": -10_000,
                "name": "ส่งคืนเงินเหลือจ่าย",
            }
        )
        rows = self._rows()
        child = rows[self.child.id]
        self.assertEqual(child["returned"], 10_000)  # g, shown positive
        self.assertEqual(child["reserved"], 0)  # b = 50 net reserve - 50 obligate
        self.assertEqual(child["used"], 50_000)  # e = net reserve
        self.assertEqual(child["remaining"], 50_000)  # f = 100 - 50
        parent = rows[self.parent.id]
        self.assertEqual(parent["returned"], 10_000)  # rolls up the tree
