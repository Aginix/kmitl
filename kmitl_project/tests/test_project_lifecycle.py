from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestProjectLifecycle(TransactionCase):
    """ลบโครงการ, the held-money guards and ปิดโครงการ (ADR-0011)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", "True")
        cls.fiscal_year = env["account.fiscal.year"].search([], limit=1)
        if not cls.fiscal_year:
            cls.fiscal_year = env["account.fiscal.year"].create(
                {
                    "name": "FY-LIFE",
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

        cls.activity = _account("activities", "Life Activity")
        cls.department = _account("departments", "Life Department")
        cls.fund = _account("funds", "Life Fund")
        cls.source = _account("sources", "Life Source")
        cls.other_department = _account("departments", "Life Other Department")

        def _budget_account(code):
            return env["budget.account"].create(
                {
                    "code": code,
                    "name": code,
                    "budget_type": "expense",
                    "budgetable": True,
                    "is_project": True,
                    "project_type": "project",
                }
            )

        cls.budget_account = _budget_account("LIFEPRJ001")
        cls.other_budget_account = _budget_account("LIFEPRJ002")

    def _make_project(self, **kw):
        vals = {
            "name": "Lifecycle Project",
            "project_type": "project",
            "account_fiscal_year_id": self.fiscal_year.id,
            "budget_account_id": self.budget_account.id,
            "activity_analytic_id": self.activity.id,
            "department_analytic_id": self.department.id,
            "fund_analytic_id": self.fund.id,
            "source_analytic_id": self.source.id,
        }
        vals.update(kw)
        return self.env["kmitl.project"].create(vals)

    def _allocate(self, project, amount):
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "account_fiscal_year_id": self.fiscal_year.id,
                "department_analytic_id": self.department.id,
                "source_analytic_id": self.source.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.budget_account.id,
                            "analytic_distribution": {
                                str(project.analytic_account_id.id): 100
                            },
                            "balance": amount,
                            "activity_analytic_id": self.activity.id,
                            "department_analytic_id": self.department.id,
                            "fund_analytic_id": self.fund.id,
                            "source_analytic_id": self.source.id,
                        },
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _approve(self, project):
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        project.action_approve()

    # -- ลบโครงการ ------------------------------------------------------------
    def test_delete_draft_without_number(self):
        project = self._make_project()
        project.action_delete()
        self.assertFalse(project.exists())

    def test_delete_without_footprint_removes_analytic(self):
        """Submitted but never funded: the project and its analytic go for good."""
        project = self._make_project()
        project.action_confirm()
        analytic = project.analytic_account_id
        self.assertTrue(analytic)
        project.action_delete()
        self.assertFalse(project.exists())
        self.assertFalse(analytic.exists())

    def test_delete_blocked_while_money_held(self):
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 1000.0)
        self.assertTrue(project.has_held_money)
        with self.assertRaises(UserError):
            project.action_delete()
        self.assertEqual(project.state, "to_verify")

    def test_soft_delete_with_footprint_and_revive(self):
        """Money came and went: the project is part of the history, so it is
        cancelled and archived with its analytic; reset to draft revives both."""
        project = self._make_project()
        project.action_confirm()
        analytic = project.analytic_account_id
        key = project.key
        move = self._allocate(project, 1000.0)
        move.button_cancel()
        self.assertFalse(project.has_held_money)
        project.action_delete()
        self.assertTrue(project.exists())
        self.assertEqual(project.state, "cancel")
        self.assertFalse(project.active)
        self.assertFalse(analytic.active)
        # The footprint also forbids the plain unlink.
        with self.assertRaises(UserError):
            project.unlink()

        project.action_draft()
        self.assertEqual(project.state, "draft")
        self.assertTrue(project.active)
        self.assertTrue(analytic.active)
        self.assertEqual(project.key, key)

    def test_delete_blocked_while_sent(self):
        project = self._make_project()
        project.action_confirm()
        project.state = "sent"
        with self.assertRaises(UserError):
            project.action_delete()

    def test_numbered_project_delete_needs_officer(self):
        """A Project Owner may delete an unnumbered draft; once the project has
        a running number only project officers may delete it."""
        owner = new_test_user(
            self.env,
            login="life_owner",
            groups="base.group_user,kmitl_project.group_kmitl_project_user",
        )
        Project = self.env["kmitl.project"].with_user(owner)
        draft = Project.create(
            {
                "name": "Owner Draft",
                "account_fiscal_year_id": self.fiscal_year.id,
            }
        )
        self.assertTrue(draft.can_delete)
        draft.action_delete()
        self.assertFalse(draft.exists())

        numbered = self._make_project(
            creating_user_id=owner.id, operating_unit_id=False
        )
        numbered.action_confirm()
        numbered = numbered.with_user(owner)
        self.assertFalse(numbered.can_delete)
        with self.assertRaises(UserError):
            numbered.action_delete()

    # -- Retarget guard ---------------------------------------------------------
    def test_retarget_blocked_while_money_held(self):
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 1000.0)
        with self.assertRaises(UserError):
            project.write({"budget_account_id": self.other_budget_account.id})
        with self.assertRaises(UserError):
            project.write({"department_analytic_id": self.other_department.id})

    def test_retarget_allowed_once_money_returned(self):
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 1000.0).button_cancel()
        project.write({"budget_account_id": self.other_budget_account.id})
        self.assertEqual(project.budget_account_id, self.other_budget_account)

    # -- ปิดโครงการ -------------------------------------------------------------
    def test_complete_returns_leftover_reservation(self):
        """Closing returns the unspent reservation (คืนจอง); the money stays at
        the project's dimension and shows under ปิดแล้วมีเงินค้าง."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 1000.0)
        self._approve(project)
        commitment = project.budget_commitment_ids
        self.assertEqual(commitment.available_to_obligate, 1000.0)
        project.action_complete()
        self.assertEqual(project.state, "complete")
        self.assertEqual(commitment.available_to_obligate, 0.0)
        self.assertIn(
            project,
            self.env["kmitl.project"].search(
                [("state", "=", "complete"), ("has_held_money", "=", True)]
            ),
        )
