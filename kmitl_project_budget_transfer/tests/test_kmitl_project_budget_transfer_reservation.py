from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestKmitlProjectBudgetTransferReservation(TransactionCase):
    """A transfer into a reserved project's coordinate tops its reservation up —
    also once spending has started (budget ADR-0016, Q5)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", False)
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-KPBL",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(plan_code, name):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_code, "code": plan_code}
            )
            return AA.create({"name": name, "plan_id": plan.id})

        cls.activity = acc("activities", "KPBL Activity")
        cls.department = acc("departments", "KPBL Department")
        cls.fund = acc("funds", "KPBL Fund")
        cls.source = acc("sources", "KPBL Source")
        cls.budget_account = env["budget.account"].create(
            {
                "code": "KPBL001",
                "name": "KPBL Project Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )
        # Floating (untagged) project pool that งานแผน allocates from.
        move = env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "appropriation_type": "initial",
                "account_fiscal_year_id": cls.fy.id,
                "department_analytic_id": cls.department.id,
                "source_analytic_id": cls.source.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": cls.budget_account.id,
                            "balance": 500_000,
                            "activity_analytic_id": cls.activity.id,
                            "fund_analytic_id": cls.fund.id,
                        }
                    )
                ],
            }
        )
        move.action_review()
        move.action_post()

    def _allocate(self, project, amount):
        """ปรับเข้าแผน: transfer from the floating pool into the project."""
        common = {
            "account_id": self.budget_account.id,
            "amount": amount,
            "activity_analytic_id": self.activity.id,
            "fund_analytic_id": self.fund.id,
            "department_analytic_id": self.department.id,
        }
        transfer = self.env["budget.transfer"].create(
            {
                "date": date.today(),
                "account_fiscal_year_id": self.fy.id,
                "department_analytic_id": self.department.id,
                "source_analytic_id": self.source.id,
                "reason": "ปรับเข้าแผน",
                "line_ids": [
                    Command.create(dict(common, transfer_direction="from")),
                    Command.create(
                        dict(
                            common,
                            transfer_direction="to",
                            kmitl_project_analytic_id=project.analytic_account_id.id,
                        )
                    ),
                ],
            }
        )
        transfer.action_submit()
        transfer.action_approve()
        return transfer

    def test_transfer_tops_up_project_reservation_after_spending(self):
        project = self.env["kmitl.project"].create(
            {
                "name": "KPBL Project",
                "project_type": "project",
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.budget_account.id,
                "activity_analytic_id": self.activity.id,
                "department_analytic_id": self.department.id,
                "fund_analytic_id": self.fund.id,
                "source_analytic_id": self.source.id,
            }
        )
        project.action_confirm()
        self._allocate(project, 100_000)
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        commitment = project.budget_commitment_ids.filtered(
            lambda c: c.state != "cancel"
        )
        self.assertEqual(commitment.amount, 100_000)

        # spending starts — the old resync could no longer act from here
        commitment._post_budget_event("obligate", 30_000)
        commitment._post_budget_event("consume", 30_000)

        self._allocate(project, 50_000)

        self.assertEqual(len(project.budget_commitment_ids), 1)
        self.assertEqual(commitment.amount, 150_000)
        self.assertEqual(commitment.total_reserved, 150_000)
        self.assertEqual(commitment.available_to_obligate, 120_000)
        self.assertEqual(commitment.total_consumed, 30_000)
        project.invalidate_recordset()
        self.assertEqual(project.budget_amount, 150_000)
        # all the project's money is reserved: nothing left at its coordinate
        self.assertEqual(
            self.env["budget.controller"].get_available(
                self.budget_account, project.analytic_distribution, self.fy.id
            ),
            0.0,
        )
