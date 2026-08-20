from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProcurementPlanBudgetTransfer(TransactionCase):
    """A transfer that funds a procurement plan's dimension to exactly its
    planned amount auto-reserves the plan (จองงบ) the moment it posts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-PPT",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )

        BA = env["budget.account"]
        cls.src = BA.create(
            {"code": "PPT_SRC", "name": "PPT Src", "budget_type": "expense"}
        )
        # The plan's รหัสงบประมาณ — a procurement-plan budget code.
        cls.proc_account = BA.create(
            {
                "code": "PPT_PROC",
                "name": "PPT Proc",
                "budget_type": "expense",
                "procurement_plan": True,
                "budgetable": True,
            }
        )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def plan(code, name):
            return Plan.search([("code", "=", code)], limit=1) or Plan.create(
                {"name": name, "code": code}
            )

        def acc(name, code, plan_code, plan_name):
            return AA.create(
                {"name": name, "code": code, "plan_id": plan(plan_code, plan_name).id}
            )

        cls.dept = acc("Dept", "PPT_DEPT", "departments", "Departments")
        cls.source = acc("Source", "PPT_SRCM", "sources", "Sources")
        cls.activity = acc("Activity", "PPT_ACT", "activities", "Activities")
        cls.fund = acc("Fund", "PPT_FUND", "funds", "Funds")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _appropriate(self, account, amount):
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": account.id,
                            "balance": amount,
                            "activity_analytic_id": self.activity.id,
                            "fund_analytic_id": self.fund.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()
        return move

    def _make_plan(self, total_price):
        plan = self.env["procurement.plan"].create(
            {
                "description": "PPT Plan %s" % total_price,
                "amount": 1,
                "unit": "ชุด",
                "total_price": total_price,
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.proc_account.id,
                "analytic_distribution": {
                    str(self.dept.id): 100,
                    str(self.source.id): 100,
                    str(self.activity.id): 100,
                    str(self.fund.id): 100,
                },
            }
        )
        plan.action_send_to_verify()  # mints the plan's procurement_plan tag
        return plan

    def _fund_plan_transfer(self, plan, amount):
        """A transfer moving ``amount`` FROM src INTO the plan's coordinate."""
        base_dims = {
            "department_analytic_id": self.dept.id,
            "activity_analytic_id": self.activity.id,
            "fund_analytic_id": self.fund.id,
        }
        transfer = self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.dept.id,
                "source_analytic_id": self.source.id,
                "line_ids": [
                    Command.create(
                        dict(
                            base_dims,
                            transfer_direction="from",
                            account_id=self.src.id,
                            amount=amount,
                        )
                    ),
                    Command.create(
                        dict(
                            base_dims,
                            transfer_direction="to",
                            account_id=self.proc_account.id,
                            procurement_plan_analytic_id=plan.analytic_account_id.id,
                            amount=amount,
                        )
                    ),
                ],
            }
        )
        return transfer

    # ------------------------------------------------------------------
    # tests
    # ------------------------------------------------------------------
    def test_full_funding_auto_reserves(self):
        self._appropriate(self.src, 5000)
        plan = self._make_plan(5000)
        transfer = self._fund_plan_transfer(plan, 5000)

        transfer.action_submit()
        transfer.action_approve()  # approve = post (base flow)

        self.assertEqual(transfer.state, "posted")
        self.assertEqual(plan.budget_amount, 5000)
        self.assertEqual(plan.state, "verified", "plan should auto-verify (จองงบ)")
        self.assertTrue(
            plan.budget_commitment_ids.filtered(lambda c: c.state != "cancel"),
            "an active reservation commitment should exist",
        )

    def test_partial_funding_does_not_reserve(self):
        self._appropriate(self.src, 5000)
        plan = self._make_plan(5000)
        transfer = self._fund_plan_transfer(plan, 3000)  # under the planned amount

        transfer.action_submit()
        transfer.action_approve()

        self.assertEqual(transfer.state, "posted")
        self.assertEqual(plan.budget_amount, 3000)
        self.assertEqual(plan.state, "to_verify", "plan must not auto-reserve")
        self.assertFalse(plan.budget_commitment_ids)
