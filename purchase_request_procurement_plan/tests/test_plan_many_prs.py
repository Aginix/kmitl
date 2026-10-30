from datetime import date
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPlanManyPrs(TransactionCase):
    """A plan may raise many purchase requests, capped at its Plan Budget
    (procurement_plan ADR-0004)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", "True")
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-PPMP",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        cls.account = env["budget.account"].create(
            {
                "code": "PPMP_PROC",
                "name": "PPMP Proc",
                "budget_type": "expense",
                "procurement_plan": True,
                "budgetable": True,
            }
        )
        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(name, code):
            plan = Plan.search([("code", "=", code)], limit=1) or Plan.create(
                {"name": code, "code": code}
            )
            return AA.create({"name": name, "plan_id": plan.id})

        cls.dims = [
            acc("PPMP Dept", "departments"),
            acc("PPMP Source", "sources"),
            acc("PPMP Activity", "activities"),
            acc("PPMP Fund", "funds"),
        ]

    def _reserved_plan(self, amount=5000):
        plan = self.env["procurement.plan"].create(
            {
                "description": "PPMP Plan",
                "amount": 1,
                "unit": "ชุด",
                "total_price": amount,
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.account.id,
                "analytic_distribution": {str(d.id): 100 for d in self.dims},
            }
        )
        plan.action_send_to_verify()
        # Allocate straight onto the plan's coordinate (its own dimension too).
        dept, source, activity, fund = self.dims
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": dept.id,
                "source_analytic_id": source.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.account.id,
                            "balance": amount,
                            "activity_analytic_id": activity.id,
                            "fund_analytic_id": fund.id,
                            "procurement_plan_analytic_id": plan.analytic_account_id.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()
        plan.invalidate_recordset()
        plan.action_verify()
        return plan

    def test_create_pr_stays_open_in_progress(self):
        plan = self._reserved_plan()
        self.assertTrue(plan.can_create_purchase_request)
        plan.action_in_progress()
        plan.invalidate_recordset(["can_create_purchase_request"])
        self.assertTrue(plan.can_create_purchase_request)
        action = plan.action_create_purchase_request()
        self.assertEqual(action["context"]["default_procurement_plan_id"], plan.id)

    def test_cap_closes_create_and_blocks_draw(self):
        plan = self._reserved_plan()
        Plan = type(plan)
        with patch.object(Plan, "_plan_pr_total", return_value=plan.budget_amount):
            plan.invalidate_recordset(["can_create_purchase_request"])
            self.assertFalse(plan.can_create_purchase_request)
            with self.assertRaisesRegex(UserError, "ครบแล้ว"):
                plan.action_create_purchase_request()
        with patch.object(Plan, "_plan_pr_total", return_value=plan.budget_amount + 1):
            with self.assertRaisesRegex(UserError, "เกินงบประมาณคงเหลือของแผน"):
                self.env["purchase.request"]._enforce_plan_budget_cap(plan)

    def test_picker_offers_plans_in_progress(self):
        pr = self.env["purchase.request"].new(
            {"budget_selection_mode": "procurement_plan"}
        )
        self.assertIn(
            ("procurement_plan_id.state", "in", ("verified", "in_progress")),
            pr._reservation_commitment_mode_domain(),
        )
