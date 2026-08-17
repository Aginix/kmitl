# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectBudgetReserve(TransactionCase):
    """Budget reserve flow on kmitl.project (ADR-0006): a project is submitted
    to งานแผน (action_confirm → to_verify, minting analytic + key), งานแผน
    allocates via a budget.move at the project's dimension, then the project
    reserves its budget.commitment via the จองงบ wizard (to_verify → to_send)."""

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
                "code": "TESTPRJ001",
                "name": "Test Project Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )

    def _make_project(self, **kw):
        vals = {
            "name": "Test Project",
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
        """Post a budget.move that allocates ``amount`` to ``project``'s dimension."""
        move = self.env["budget.move"].create(
            {
                "move_type": "appropriation",
                "budget_type": "expense",
                "account_fiscal_year_id": self.fiscal_year.id,
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

    def _reserve(self, project):
        """Use the wizard to reserve budget (to_verify → to_send)."""
        wizard = self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        )
        wizard.action_confirm()

    def test_confirm_mints_analytic_and_key(self):
        """action_confirm (draft→to_verify) mints key + analytic account."""
        project = self._make_project()
        self.assertFalse(project.key)
        self.assertFalse(project.analytic_account_id)

        project.action_confirm()

        self.assertEqual(project.state, "to_verify")
        self.assertTrue(project.key)
        self.assertTrue(project.analytic_account_id)
        self.assertEqual(project.analytic_account_id.plan_id.code, "kmitl_project")

    def test_budget_amount_zero_before_allocation(self):
        """budget_amount == 0 in draft and in to_verify before any allocation."""
        project = self._make_project()
        self.assertEqual(project.budget_amount, 0.0)
        project.action_confirm()
        self.assertEqual(project.budget_amount, 0.0)

    def test_reserve_blocked_without_allocation(self):
        """จองงบ raises UserError when budget_amount == 0."""
        project = self._make_project()
        project.action_confirm()
        self.assertEqual(project.budget_amount, 0.0)
        with self.assertRaises(UserError):
            project.action_reserve_budget()

    def test_allocation_sets_budget_amount(self):
        """After a posted allocation move at the project dim, budget_amount is set."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self.assertAlmostEqual(project.budget_amount, 100000.0)

    def test_reserve_after_allocation(self):
        """Full flow: confirm → allocate → reserve (wizard) → to_send with commitment."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self.assertEqual(project.budget_amount, 100000.0)

        self._reserve(project)

        self.assertEqual(project.state, "to_send")
        self.assertEqual(len(project.budget_commitment_ids), 1)
        commitment = project.budget_commitment_ids
        self.assertEqual(commitment.state, "reserved")
        self.assertEqual(commitment.amount, 100000.0)
        self.assertEqual(commitment.kmitl_project_id, project)
        self.assertIn(
            str(project.analytic_account_id.id),
            commitment.analytic_distribution or {},
        )

    def test_commitment_carries_project_dim(self):
        """The commitment's analytic_distribution includes the kmitl_project dim."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 50000.0)
        self._reserve(project)
        commitment = project.budget_commitment_ids
        self.assertIn(
            str(project.analytic_account_id.id),
            commitment.analytic_distribution or {},
        )

    def test_budget_remaining_starts_at_full_reserved(self):
        """budget_remaining = reserved − consumed; right after reserve nothing consumed."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self._reserve(project)
        self.assertAlmostEqual(project.budget_remaining, 100000.0)

    def test_reserve_is_idempotent(self):
        """Re-running _reserve_project_commitment does not create a second commitment."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self._reserve(project)
        self.assertEqual(len(project.budget_commitment_ids), 1)
        project._reserve_project_commitment()
        self.assertEqual(len(project.budget_commitment_ids), 1)

    def test_cancel_releases_untouched_commitment(self):
        """Cancelling a project that has not yet spent cancels its reservation."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self._reserve(project)
        commitment = project.budget_commitment_ids
        project.action_cancel()
        self.assertEqual(project.state, "cancel")
        self.assertEqual(commitment.state, "cancel")

    def test_cancel_keeps_commitment_when_in_progress(self):
        """Cancelling an in-progress project keeps its commitment."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self._reserve(project)
        project.action_approve()
        self.assertEqual(project.state, "in_progress")
        commitment = project.budget_commitment_ids
        project.action_cancel()
        self.assertEqual(project.state, "cancel")
        self.assertEqual(commitment.state, "reserved")

    def test_confirm_runs_exception_gate(self):
        """ส่งเข้าแผน runs detect_exceptions: a Strategic Project missing strategic-plan
        pops the wizard and stays draft (no mint), and goes through once ignored."""
        project = self._make_project(project_type="strategic_project")
        action = project.action_confirm()
        self.assertEqual(project.state, "draft")
        self.assertFalse(project.key)
        self.assertTrue(project.exception_ids)
        self.assertEqual(action.get("res_model"), "kmitl.project.exception.confirm")

        project.ignore_exception = True
        project.action_confirm()
        self.assertEqual(project.state, "to_verify")
        self.assertTrue(project.key)

    def test_reject_blocked_once_approved(self):
        """An executing project is past the point of refusal."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self._reserve(project)
        project.action_approve()
        with self.assertRaises(UserError):
            project.action_reject()

    def test_cancel_blocked_when_complete(self):
        """A finished project cannot be cancelled."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self._reserve(project)
        project.action_approve()
        project.action_complete()
        with self.assertRaises(UserError):
            project.action_cancel()

    def test_fiscal_year_sticky_after_confirm(self):
        """ปีงบ freezes for good once the running number is minted (only ปีงบ is
        sticky; the rest of the budget target is not)."""
        project = self._make_project()
        self.assertFalse(project.budget_target_locked)
        project.action_confirm()
        self.assertTrue(project.budget_target_locked)
        other_fy = self.env["account.fiscal.year"].create(
            {
                "name": "FY-TEST-2",
                "date_from": date(2026, 10, 1),
                "date_to": date(2027, 9, 30),
                "company_id": self.env.company.id,
            }
        )
        with self.assertRaises(UserError):
            project.write({"account_fiscal_year_id": other_fy.id})

    def test_budget_code_editable_in_to_verify(self):
        """รหัสงบ stays editable after ส่งเข้าแผน (to_verify), before the budget is reserved."""
        project = self._make_project()
        project.action_confirm()
        self.assertEqual(project.state, "to_verify")
        other_account = self.env["budget.account"].create(
            {
                "code": "TESTPRJ002",
                "name": "Other Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )
        # No raise — the budget target is editable in the pre-reserve band.
        project.write({"budget_account_id": other_account.id})
        self.assertEqual(project.budget_account_id, other_account)

    def test_budget_target_stays_locked_after_reset(self):
        """After reset-to-draft, budget_target_locked stays True (key survives)."""
        project = self._make_project()
        project.action_confirm()
        self.assertTrue(project.key)
        project.action_draft()
        self.assertEqual(project.state, "draft")
        self.assertTrue(project.budget_target_locked)

    def test_budget_target_locked_after_reserve(self):
        """Once the budget is reserved (to_send), the budget target pins: a direct
        department_analytic_id / analytic_distribution budget-dim change raises."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self._reserve(project)
        self.assertEqual(project.state, "to_send")
        other_dept = self.env["account.analytic.account"].create(
            {
                "name": "Other Dept",
                "plan_id": self.env["account.analytic.plan"].search(
                    [("code", "=", "departments")], limit=1
                ).id,
            }
        )
        with self.assertRaises(UserError):
            project.write({"department_analytic_id": other_dept.id})

    def test_analytic_distribution_dims_editable_before_reserve(self):
        """Swapping a budget-dim key in analytic_distribution is allowed in to_verify
        (pre-reserve); the locked-once-reserved case is covered by the department test."""
        project = self._make_project()
        project.action_confirm()
        other_activity = self.env["account.analytic.account"].create(
            {
                "name": "Other Activity",
                "plan_id": self.env["account.analytic.plan"].search(
                    [("code", "=", "activities")], limit=1
                ).id,
            }
        )
        dist = dict(project.analytic_distribution or {})
        dist.pop(str(self.activity.id), None)
        dist[str(other_activity.id)] = 100
        # No raise — editable in the pre-reserve band.
        project.write({"analytic_distribution": dist})

    def test_analytic_distribution_project_key_allowed_after_confirm(self):
        """Adding the kmitl_project dim key to analytic_distribution is allowed even
        after key is set (this is what _ensure_analytic_account does)."""
        project = self._make_project()
        project.action_confirm()
        # The project now has analytic_account_id from action_confirm.
        # The kmitl_project key should already be in analytic_distribution.
        # Simulate writing the same distribution again (no-op change) — should not raise.
        project.write({"analytic_distribution": dict(project.analytic_distribution or {})})

    def test_auto_resync_on_allocation_change(self):
        """After a top-up allocation move, budget_amount rises and if commitment
        exists it is re-synced to the new amount (pre-spending)."""
        project = self._make_project()
        project.action_confirm()
        self._allocate(project, 100000.0)
        self._reserve(project)
        self.assertAlmostEqual(project.budget_amount, 100000.0)
        commitment = project.budget_commitment_ids.filtered(lambda c: c.state != "cancel")
        self.assertAlmostEqual(commitment.amount, 100000.0)

        self._allocate(project, 50000.0)

        project.invalidate_recordset()
        self.assertAlmostEqual(project.budget_amount, 150000.0)
        active = project.budget_commitment_ids.filtered(lambda c: c.state != "cancel")
        self.assertAlmostEqual(active.amount, 150000.0)

    def test_isolation_two_projects(self):
        """Two projects sharing the four base dims do not cross-deplete each other."""
        p1 = self._make_project(name="Project 1")
        p2 = self._make_project(name="Project 2")
        p1.action_confirm()
        p2.action_confirm()
        # Allocate separately to each project
        self._allocate(p1, 100000.0)
        self._allocate(p2, 80000.0)
        self.assertAlmostEqual(p1.budget_amount, 100000.0)
        self.assertAlmostEqual(p2.budget_amount, 80000.0)
        # Reserve both
        self._reserve(p1)
        self._reserve(p2)
        self.assertEqual(p1.state, "to_send")
        self.assertEqual(p2.state, "to_send")

    def test_is_project_excludes_procurement_plan(self):
        """A budget code cannot be both a project code and a procurement-plan code."""
        BA = self.env["budget.account"]
        if "procurement_plan" not in BA._fields:
            self.skipTest("procurement_plan module not installed")
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
