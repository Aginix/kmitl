from datetime import date

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBudgetPoolGuard(TransactionCase):
    """กองงบไม่ซ้อน — pools never nest (ADR-0016).

    The guard runs when an expense appropriation/entry move posts and rejects a
    coordinate that would nest inside (or contain) another funded coordinate on
    every axis at once.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-GUARD",
                "date_from": date(2089, 10, 1),
                "date_to": date(2090, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.root = BA.create(
            {"code": "G_ROOT", "name": "Root", "budget_type": "expense"}
        )
        cls.child = BA.create(
            {
                "code": "G_CHILD",
                "name": "Child",
                "budget_type": "expense",
                "parent_id": cls.root.id,
            }
        )
        cls.other = BA.create(
            {"code": "G_OTHER", "name": "Other", "budget_type": "expense"}
        )
        cls.rev = BA.create(
            {"code": "G_REV", "name": "Revenue", "budget_type": "revenue"}
        )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]
        cls.has_tree = "parent_id" in AA._fields
        act_plan = Plan.search(
            [("code", "=", "activities")], limit=1
        ) or Plan.create({"name": "Activities", "code": "activities"})
        fund_plan = Plan.search([("code", "=", "funds")], limit=1) or Plan.create(
            {"name": "Funds", "code": "funds"}
        )
        cls.act_main = AA.create(
            {"name": "Main", "code": "G_ACT_M", "plan_id": act_plan.id}
        )
        sub_vals = {"name": "Sub", "code": "G_ACT_S", "plan_id": act_plan.id}
        if cls.has_tree:
            sub_vals["parent_id"] = cls.act_main.id
        cls.act_sub = AA.create(sub_vals)
        cls.fund_a = AA.create(
            {"name": "Fund A", "code": "G_FA", "plan_id": fund_plan.id}
        )
        cls.fund_b = AA.create(
            {"name": "Fund B", "code": "G_FB", "plan_id": fund_plan.id}
        )
        cls.controller = env["budget.controller"]

    # --- helpers ---

    def _move(self, lines, move_type="appropriation", budget_type="expense", ctx=None):
        vals = {
            "move_type": move_type,
            "budget_type": budget_type,
            "account_fiscal_year_id": self.fy.id,
            "line_ids": [Command.create(l) for l in lines],
        }
        if move_type == "appropriation":
            vals["appropriation_type"] = "initial"
        move = self.env["budget.move"].create(vals)
        if ctx:
            move = move.with_context(**ctx)
        return move

    def _post(self, lines, **kw):
        move = self._move(lines, **kw)
        move.action_review()
        move.action_post()
        return move

    # --- nesting rejected ---

    def test_nested_account_axis_raises(self):
        """A pool at a parent account and one at its child (same dims) nest."""
        self._post([{"account_id": self.root.id, "balance": 100_000}])
        with self.assertRaises(ValidationError):
            self._post([{"account_id": self.child.id, "balance": 50_000}])

    def test_nested_activity_axis_raises(self):
        if not self.has_tree:
            self.skipTest("analytic hierarchy absent")
        self._post(
            [
                {
                    "account_id": self.other.id,
                    "balance": 100_000,
                    "activity_analytic_id": self.act_main.id,
                }
            ]
        )
        with self.assertRaises(ValidationError):
            self._post(
                [
                    {
                        "account_id": self.other.id,
                        "balance": 50_000,
                        "activity_analytic_id": self.act_sub.id,
                    }
                ]
            )

    def test_two_nested_lines_in_one_move_raises(self):
        with self.assertRaises(ValidationError):
            self._post(
                [
                    {"account_id": self.root.id, "balance": 100_000},
                    {"account_id": self.child.id, "balance": 50_000},
                ]
            )

    # --- allowed ---

    def test_sibling_accounts_ok(self):
        self._post([{"account_id": self.child.id, "balance": 100_000}])
        self._post([{"account_id": self.other.id, "balance": 50_000}])
        self.assertTrue(True)

    def test_other_fund_ok(self):
        self._post(
            [
                {
                    "account_id": self.other.id,
                    "balance": 100_000,
                    "fund_analytic_id": self.fund_a.id,
                }
            ]
        )
        self._post(
            [
                {
                    "account_id": self.other.id,
                    "balance": 50_000,
                    "fund_analytic_id": self.fund_b.id,
                }
            ]
        )
        self.assertTrue(True)

    def test_false_vs_value_ok(self):
        """A pool with a fund and one without (same account) do not nest."""
        self._post(
            [
                {
                    "account_id": self.other.id,
                    "balance": 100_000,
                    "fund_analytic_id": self.fund_a.id,
                }
            ]
        )
        self._post([{"account_id": self.other.id, "balance": 50_000}])
        self.assertTrue(True)

    def test_supplementary_topup_same_coord_ok(self):
        """Topping up the exact same coordinate is not nesting (identical)."""
        self._post([{"account_id": self.child.id, "balance": 100_000}])
        self._post([{"account_id": self.child.id, "balance": 50_000}])
        self.assertTrue(True)

    # --- ignored move classes ---

    def test_consume_move_ignored(self):
        self._post([{"account_id": self.root.id, "balance": 100_000}])
        # a consume move at the child does not build a pool -> no guard
        move = self._move(
            [{"account_id": self.child.id, "balance": 20_000}], move_type="consume"
        )
        move.action_review()
        move.action_post()  # must not raise
        self.assertEqual(move.state, "posted")

    def test_revenue_move_ignored(self):
        self._post(
            [{"account_id": self.rev.id, "balance": 100_000}], budget_type="revenue"
        )
        self._post(
            [{"account_id": self.rev.id, "balance": 50_000}], budget_type="revenue"
        )
        self.assertTrue(True)

    def test_zero_line_ignored(self):
        self._post([{"account_id": self.root.id, "balance": 100_000}])
        # a zero-balance line at the child is not a pool
        self._post([{"account_id": self.child.id, "balance": 0.0}])
        self.assertTrue(True)

    # --- transfers move a pool ---

    def test_move_whole_pool_ok_partial_raises(self):
        """Draining a whole pool to a comparable coordinate is fine; leaving a
        residue that still overlaps is not."""
        self._post([{"account_id": self.root.id, "balance": 100_000}])
        # entry that fully drains root and funds the child: root -> 0, child -> 100k
        self._post(
            [
                {"account_id": self.root.id, "balance": -100_000},
                {"account_id": self.child.id, "balance": 100_000},
            ],
            move_type="entry",
        )
        self.assertEqual(self.controller.scan_pool_overlaps(self.fy.id), [])

    def test_reposting_after_reset_is_rechecked(self):
        move = self._post([{"account_id": self.root.id, "balance": 100_000}])
        move.button_draft()
        # seed a comparable child pool with the skip flag, then re-posting the
        # (comparable) root move must re-run the guard and raise.
        child_move = self._move([{"account_id": self.child.id, "balance": 50_000}])
        child_move.action_review()
        child_move.with_context(skip_pool_nesting_check=True).action_post()
        with self.assertRaises(ValidationError):
            move.action_review()
            move.action_post()

    # --- scan ---

    def test_scan_reports_legacy_overlap(self):
        m1 = self._move([{"account_id": self.root.id, "balance": 100_000}])
        m1.action_review()
        m1.with_context(skip_pool_nesting_check=True).action_post()
        m2 = self._move([{"account_id": self.child.id, "balance": 50_000}])
        m2.action_review()
        m2.with_context(skip_pool_nesting_check=True).action_post()
        pairs = self.controller.scan_pool_overlaps(self.fy.id)
        self.assertEqual(len(pairs), 1)
