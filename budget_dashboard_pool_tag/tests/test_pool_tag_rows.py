from datetime import date
from unittest.mock import patch

from odoo import Command
from odoo.tests.common import TransactionCase, tagged

_TAG = {
    "field": "kmitl_project_analytic_id",
    "label": "โครงการ/กิจกรรม",
    "toggle_label": "แสดงโครงการ/กิจกรรม",
    "res_model": False,
}
_VALUE_KEYS = (
    "initial",
    "current",
    "cap",
    "reserved",
    "obligated",
    "consumed",
    "used",
    "remaining",
    "returned",
)


@tagged("post_install", "-at_install")
class TestPoolTagRows(TransactionCase):
    """Pool Tag item rows hang under the code holding them and reconcile."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-POOLTAG",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        BA = env["budget.account"]
        cls.parent = BA.create(
            {
                "code": "PTAG00",
                "name": "Pool Tag Parent",
                "budget_type": "expense",
                "budgetable": False,
            }
        )
        cls.tagged_code = BA.create(
            {
                "code": "PTAG01",
                "name": "Pool Tag Code",
                "budget_type": "expense",
                "budgetable": True,
                "parent_id": cls.parent.id,
            }
        )
        cls.plain_code = BA.create(
            {
                "code": "PTAG02",
                "name": "Plain Code",
                "budget_type": "expense",
                "budgetable": True,
                "parent_id": cls.parent.id,
            }
        )
        Plan = env["account.analytic.plan"]
        plan = Plan.search([("code", "=", "kmitl_project")], limit=1) or Plan.create(
            {"name": "โครงการ/กิจกรรม", "code": "kmitl_project"}
        )
        cls.project = env["account.analytic.account"].create(
            {"name": "Project PT", "code": "PTAGPRJ", "plan_id": plan.id}
        )
        cls.dist = {str(cls.project.id): 100.0}

    def setUp(self):
        super().setUp()
        dashboard_cls = type(self.env["budget.dashboard"])
        patcher = patch.object(dashboard_cls, "_pool_tags", lambda self: [_TAG])
        patcher.start()
        self.addCleanup(patcher.stop)

    # --- helpers ---

    def _appropriate(self, account, amount, dist=None):
        line = {"account_id": account.id, "balance": amount}
        if dist:
            line["analytic_distribution"] = dist
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "line_ids": [Command.create(line)],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _reserve(self, account, amount, dist):
        commitment = self.env["budget.commitment"].create(
            {
                "date": date.today(),
                "title": "Pool tag commitment",
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

    def _setup_money(self):
        self._appropriate(self.tagged_code, 100_000)  # floating / untagged
        self._appropriate(self.tagged_code, 30_000, self.dist)  # allocated
        self._reserve(self.tagged_code, 20_000, self.dist)
        self._appropriate(self.plain_code, 50_000)

    def _items(self, breakdown=None, tag_fields=("kmitl_project_analytic_id",)):
        return self.env["budget.dashboard"].get_pool_tag_rows(
            self.fy.id, self.parent.id, {}, breakdown, list(tag_fields)
        )

    # --- tests ---

    def test_items_under_holding_code_with_residual(self):
        self._setup_money()
        items = self._items()
        self.assertEqual(
            {row["account_id"] for row in items},
            {self.tagged_code.id},
            "only the code holding tagged lines gets item rows",
        )
        project, residual = items  # tagged first, untagged remainder last
        self.assertEqual(project["analytic_id"], self.project.id)
        self.assertEqual(project["tag_field"], "kmitl_project_analytic_id")
        self.assertEqual(project["current"], 30_000)
        self.assertEqual(project["cap"], 20_000)
        self.assertEqual(project["used"], 20_000)
        self.assertEqual(project["remaining"], 10_000)
        self.assertFalse(residual["analytic_id"])
        self.assertEqual(residual["current"], 100_000)
        self.assertEqual(residual["used"], 0)

    def test_items_reconcile_with_code_row(self):
        self._setup_money()
        for breakdown in (None, ["activity_analytic_id"]):
            rows = self.env["budget.dashboard"].get_dashboard_data(
                self.fy.id, self.parent.id, {}, breakdown
            )["rows"]
            code_row = next(
                r
                for r in rows
                if r["row_type"] == "account" and r["account_id"] == self.tagged_code.id
            )
            items = self._items(breakdown)
            for key in _VALUE_KEYS:
                self.assertAlmostEqual(
                    sum(item[key] for item in items),
                    code_row[key],
                    msg="%s (breakdown=%s)" % (key, breakdown),
                )

    def test_no_tag_enabled_returns_nothing(self):
        self._setup_money()
        self.assertEqual(self._items(tag_fields=()), [])

    def test_reservation_grid_has_no_items(self):
        self._setup_money()
        rows = self.env["budget.dashboard"].get_reservation_grid(
            self.fy.id, {}, self.parent.id
        )["rows"]
        self.assertFalse([r for r in rows if r.get("row_type") == "pool_tag"])
