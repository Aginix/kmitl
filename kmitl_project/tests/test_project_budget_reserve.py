# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectBudgetReserve(TransactionCase):
    """The floating-budget reserve flow on kmitl.project (ADR-0005/0007): a project
    reserves one shared budget.commitment for its full budget_amount at the
    budget-reservation step (action_reserve_budget, to_verify→to_send), and
    releases it while untouched on reject/cancel/reset-to-draft."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # Skip the pool availability check so the reserve mechanism can be tested
        # in isolation (no funded appropriation needed).
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
                "code": "TESTPRJ001",
                "name": "Test Project Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )

    def _make_project(self, amount=100000.0, **kw):
        vals = {
            "name": "Test Project",
            "project_type": "project",
            "account_fiscal_year_id": self.fiscal_year.id,
            "budget_account_id": self.budget_account.id,
            "budget_amount": amount,
            "activity_analytic_id": self.activity.id,
            "department_analytic_id": self.department.id,
            "fund_analytic_id": self.fund.id,
            "source_analytic_id": self.source.id,
        }
        vals.update(kw)
        return self.env["kmitl.project"].create(vals)

    def test_confirm_reserves_commitment(self):
        """action_reserve_budget reserves one commitment for the full
        budget_amount and the project auto-gets its kmitl_project analytic."""
        project = self._make_project(amount=100000.0)
        self.assertEqual(project.state, "draft")
        self.assertFalse(project.budget_commitment_ids)

        project.action_confirm()
        self.assertEqual(project.state, "to_verify")
        project.action_reserve_budget()

        self.assertEqual(project.state, "to_send")
        self.assertEqual(len(project.budget_commitment_ids), 1)
        commitment = project.budget_commitment_ids
        self.assertEqual(commitment.state, "reserved")
        self.assertEqual(commitment.amount, 100000.0)
        self.assertEqual(commitment.total_reserved, 100000.0)
        self.assertEqual(commitment.kmitl_project_id, project)
        # The kmitl_project analytic dimension is created and carried.
        self.assertTrue(project.analytic_account_id)
        self.assertEqual(
            project.analytic_account_id.plan_id.code, "kmitl_project"
        )
        self.assertIn(
            str(project.analytic_account_id.id),
            commitment.analytic_distribution or {},
        )

    def test_budget_remaining_starts_at_full_reserved(self):
        """budget_remaining = reserved − consumed; right after confirm nothing is
        consumed, so it equals the full budget_amount."""
        project = self._make_project(amount=100000.0)
        project.action_confirm()
        project.action_reserve_budget()
        self.assertEqual(project.budget_remaining, 100000.0)

    def test_reserve_is_idempotent(self):
        """Re-running the reservation does not create a second commitment."""
        project = self._make_project()
        project.action_confirm()
        project.action_reserve_budget()
        self.assertEqual(len(project.budget_commitment_ids), 1)
        project._reserve_project_commitment()
        self.assertEqual(len(project.budget_commitment_ids), 1)

    def test_confirm_requires_positive_amount(self):
        """Confirming with a non-positive budget_amount is blocked."""
        project = self._make_project(amount=0.0)
        project.action_confirm()
        with self.assertRaises(UserError):
            project.action_reserve_budget()

    def test_cancel_releases_untouched_commitment(self):
        """Cancelling a project that has not yet spent cancels its reservation."""
        project = self._make_project()
        project.action_confirm()
        project.action_reserve_budget()
        commitment = project.budget_commitment_ids
        project.action_cancel()
        self.assertEqual(project.state, "cancel")
        self.assertEqual(commitment.state, "cancel")

    def test_cancel_keeps_commitment_when_in_progress(self):
        """Cancelling an in-progress project keeps its commitment so in-flight
        spend is never stranded (release-before-write sees state in_progress)."""
        project = self._make_project()
        project.action_confirm()
        project.action_reserve_budget()
        project.action_approve()
        self.assertEqual(project.state, "in_progress")
        commitment = project.budget_commitment_ids
        project.action_cancel()
        self.assertEqual(project.state, "cancel")
        self.assertEqual(commitment.state, "reserved")

    def test_confirm_runs_exception_gate(self):
        """ยืนยัน runs detect_exceptions (ADR-0005): a Strategic Project missing a
        strategic-plan level pops the wizard and stays draft, and goes through once
        the exception is ignored."""
        project = self._make_project(project_type="strategic_project")
        action = project.action_confirm()
        self.assertEqual(project.state, "draft")
        self.assertTrue(project.exception_ids)
        self.assertEqual(action.get("res_model"), "kmitl.project.exception.confirm")

        project.ignore_exception = True
        project.action_confirm()
        self.assertEqual(project.state, "to_verify")

    def test_reject_blocked_once_approved(self):
        """An executing project is past the point of refusal."""
        project = self._make_project()
        project.action_confirm()
        project.action_reserve_budget()
        project.action_approve()
        with self.assertRaises(UserError):
            project.action_reject()

    def test_cancel_blocked_when_complete(self):
        """A finished project cannot be cancelled."""
        project = self._make_project()
        project.action_confirm()
        project.action_reserve_budget()
        project.action_approve()
        project.action_complete()
        with self.assertRaises(UserError):
            project.action_cancel()

    def test_returned_edit_resyncs_commitment(self):
        """`returned` reopens budget_amount, so re-sending re-reserves at the new
        figure: the stale commitment is cancelled and a fresh one replaces it."""
        project = self._make_project(amount=100000.0)
        project.action_confirm()
        project.action_reserve_budget()
        stale = project.budget_commitment_ids
        project.state = "returned"
        project.budget_amount = 60000.0

        project._resync_project_commitment()

        self.assertEqual(stale.state, "cancel")
        active = project.budget_commitment_ids.filtered(
            lambda c: c.state != "cancel"
        )
        self.assertEqual(len(active), 1)
        self.assertEqual(active.amount, 60000.0)

    def test_is_project_excludes_procurement_plan(self):
        """A budget code cannot be both a project code and a procurement-plan code."""
        BA = self.env["budget.account"]
        if "procurement_plan" not in BA._fields:
            self.skipTest("procurement_plan module not installed")
        # is_project first, then procurement_plan -> blocked
        acc = BA.create(
            {
                "code": "TESTEXC1",
                "name": "Excl 1",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
            }
        )
        with self.assertRaises(ValidationError):
            acc.procurement_plan = True
        # procurement_plan first, then is_project -> also blocked
        acc2 = BA.create(
            {
                "code": "TESTEXC2",
                "name": "Excl 2",
                "budget_type": "expense",
                "budgetable": True,
                "procurement_plan": True,
            }
        )
        with self.assertRaises(ValidationError):
            acc2.is_project = True
