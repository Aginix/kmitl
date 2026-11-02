# -*- coding: utf-8 -*-
from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestApproveReserves(TransactionCase):
    """หนังสือลงนามครบ approves the project AND reserves its budget
    (kmitl_project ADR-0010), even though the last signer holds no budget
    rights — the engine dispatches the callback on ``origin.sudo()``."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", "True")

        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-TEST",
                    "date_from": date(2025, 10, 1),
                    "date_to": date(2026, 9, 30),
                    "company_id": env.company.id,
                }
            )

        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def _account(plan_code, name):
            plan = Plan.search([("code", "=", plan_code)], limit=1)
            if not plan:
                plan = Plan.create({"name": plan_code, "code": plan_code})
            return AA.create({"name": name, "plan_id": plan.id})

        cls.activity = _account("activities", "Test Activity")
        cls.department = _account("departments", "Test Department")
        cls.fund = _account("funds", "Test Fund")
        cls.source = _account("sources", "Test Source")
        cls.budget_account = env["budget.account"].create(
            {
                "code": "TESTPRJSRB",
                "name": "Test Project Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )
        cls.signer = env["res.users"].create(
            {
                "name": "Dean",
                "login": "kp_sarabun_dean",
                "groups_id": [Command.set([env.ref("base.group_user").id])],
            }
        )

    def _sent_project(self):
        project = self.env["kmitl.project"].create(
            {
                "name": "Test Project",
                "project_type": "project",
                "account_fiscal_year_id": self.fiscal_year.id,
                "budget_account_id": self.budget_account.id,
                "activity_analytic_id": self.activity.id,
                "department_analytic_id": self.department.id,
                "fund_analytic_id": self.fund.id,
                "source_analytic_id": self.source.id,
            }
        )
        project.action_confirm()
        self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "account_fiscal_year_id": self.fiscal_year.id,
                "department_analytic_id": self.department.id,
                "source_analytic_id": self.source.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.budget_account.id,
                            "analytic_distribution": {
                                str(project.analytic_account_id.id): 100
                            },
                            "balance": 100000.0,
                            "activity_analytic_id": self.activity.id,
                            "department_analytic_id": self.department.id,
                            "fund_analytic_id": self.fund.id,
                            "source_analytic_id": self.source.id,
                        }
                    )
                ],
            }
        ).action_post()
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        project.state = "sent"
        self.assertFalse(project.budget_commitment_ids)
        return project

    def _complete_as_signer(self, project):
        # Mirrors sarabun.document._call_origin: origin.sudo() in the signer's env.
        project.with_user(self.signer).sudo()._on_sarabun_completed(
            self.env["sarabun.document"]
        )

    def test_completed_reserves_budget(self):
        project = self._sent_project()
        self._complete_as_signer(project)
        self.assertEqual(project.state, "in_progress")
        commitment = project.budget_commitment_ids
        self.assertEqual(len(commitment), 1)
        self.assertEqual(commitment.state, "reserved")
        self.assertEqual(commitment.amount, 100000.0)
        self.assertEqual(commitment.user_id, project.creating_user_id)

    def test_completed_keeps_legacy_reservation(self):
        project = self._sent_project()
        project._reserve_project_commitment()  # legacy: reserved before approval
        commitment = project.budget_commitment_ids
        self._complete_as_signer(project)
        self.assertEqual(project.state, "in_progress")
        self.assertEqual(project.budget_commitment_ids, commitment)
