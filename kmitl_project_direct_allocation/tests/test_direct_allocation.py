from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDirectAllocation(TransactionCase):
    """จัดสรรและจองงบประมาณ (ADR-0009): งานแผน moves floating money into the
    project's dimension through an immediately-posted transfer, then reserves
    (to_verify → to_send) — one transaction."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        # kmitl_demo turns this on, which would no-op every availability check.
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", False)
        cls.fy = env["account.fiscal.year"].search([], limit=1) or env[
            "account.fiscal.year"
        ].create(
            {
                "name": "FY-KPDA",
                "date_from": date(2025, 10, 1),
                "date_to": date(2026, 9, 30),
                "company_id": env.company.id,
            }
        )
        cls.ba = env["budget.account"].create(
            {
                "code": "KPDA_PROJBA",
                "name": "KPDA Project BA",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )
        Plan = env["account.analytic.plan"]
        AA = env["account.analytic.account"]

        def acc(name, plan_code):
            plan = Plan.search([("code", "=", plan_code)], limit=1) or Plan.create(
                {"name": plan_code, "code": plan_code}
            )
            return AA.create({"name": name, "plan_id": plan.id})

        cls.dept = acc("KPDA Dept", "departments")
        cls.source = acc("KPDA Source", "sources")
        cls.activity = acc("KPDA Activity", "activities")
        cls.fund = acc("KPDA Fund", "funds")

        # Floating pool: the project's coordinate, no project dimension.
        move = env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "account_fiscal_year_id": cls.fy.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": cls.ba.id,
                            "balance": 1000.0,
                            "activity_analytic_id": cls.activity.id,
                            "department_analytic_id": cls.dept.id,
                            "fund_analytic_id": cls.fund.id,
                            "source_analytic_id": cls.source.id,
                        },
                    )
                ],
            }
        )
        move.action_post()

    def _project(self, expense=300.0):
        project = self.env["kmitl.project"].create(
            {
                "name": "KPDA Project",
                "project_type": "project",
                "account_fiscal_year_id": self.fy.id,
                "budget_account_id": self.ba.id,
                "activity_analytic_id": self.activity.id,
                "department_analytic_id": self.dept.id,
                "fund_analytic_id": self.fund.id,
                "source_analytic_id": self.source.id,
                "expense_line_ids": [(0, 0, {"name": "ค่าใช้สอย", "amount": expense})],
            }
        )
        project.action_confirm()
        self.assertEqual(project.state, "to_verify")
        return project

    def _wizard(self, project, **vals):
        return (
            self.env["kmitl.project.direct.allocation"]
            .with_context(default_project_id=project.id)
            .create(vals)
        )

    def _transfers(self, project):
        return self.env["budget.transfer"].search(
            [
                (
                    "line_ids.kmitl_project_analytic_id",
                    "=",
                    project.analytic_account_id.id,
                )
            ]
        )

    def test_default_amount_is_plan_expense_minus_allocated(self):
        project = self._project(expense=300.0)
        self.assertEqual(self._wizard(project).amount, 300.0)

    def test_allocate_and_reserve(self):
        project = self._project(expense=300.0)
        self._wizard(project).action_confirm()

        transfer = self._transfers(project)
        self.assertEqual(len(transfer), 1)
        self.assertEqual(transfer.state, "posted")
        self.assertEqual(transfer.approver_id, self.env.user)
        self.assertEqual(project.budget_amount, 300.0)
        commitment = project.budget_commitment_ids
        self.assertEqual(len(commitment), 1)
        self.assertEqual(commitment.amount, 300.0)
        self.assertEqual(project.state, "to_send")

    def test_insufficient_floating_rolls_back(self):
        project = self._project()
        with self.assertRaises((UserError, ValidationError)):
            self._wizard(project, amount=5000.0).action_confirm()
        self.assertFalse(self._transfers(project))
        self.assertEqual(project.budget_amount, 0.0)
        self.assertEqual(project.state, "to_verify")

    def test_non_budget_user_blocked(self):
        user = self.env["res.users"].create(
            {
                "name": "KPDA Officer",
                "login": "kpda_officer",
                "groups_id": [
                    (
                        6,
                        0,
                        [self.env.ref("kmitl_project.group_kmitl_project_user_all").id],
                    )
                ],
            }
        )
        project = self._project()
        wizard = self._wizard(project)
        with self.assertRaises((AccessError, UserError)):
            wizard.with_user(user).action_confirm()
        self.assertEqual(project.state, "to_verify")
