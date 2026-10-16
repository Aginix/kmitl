from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProcurementUnderProject(TransactionCase):
    """A พ.1 names the โครงการ/กิจกรรม it is bought under on its own form
    (จัดซื้อภายใต้, root ADR-0011): choosing the project fills and locks its
    budget context, Reserve waits for the project's approval and then draws the
    project's single commitment, and the project's headroom counts a พ.1 only
    once it has drawn."""

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

        cls.product = env["product.product"].create(
            {"name": "Test Project Product", "type": "consu"}
        )
        cls.budget_account = env["budget.account"].create(
            {
                "code": "TESTPRJ010",
                "name": "Test Project Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
                "purchase_ok": True,
                "product_id": cls.product.id,
            }
        )

    def _make_project(self):
        return self.env["kmitl.project"].create(
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

    def _reserved_project(self, amount=100000.0):
        """ส่งเข้าแผน → ปรับเข้าแผน (allocation) → จองงบ: ``to_send`` with a live
        commitment, the หนังสือ not yet signed (kmitl_project ADR-0005/0006)."""
        project = self._make_project()
        project.action_confirm()
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
        self.env["kmitl.project.reserve.confirm"].create(
            {"project_id": project.id}
        ).action_confirm()
        self.assertEqual(project.state, "to_send")
        return project

    def _make_pr(self, project, cost=1000.0):
        return self.env["purchase.request"].create(
            {
                "title": "Test PR",
                "requested_by": self.env.ref("base.user_admin").id,
                "account_fiscal_year_id": self.fiscal_year.id,
                "budget_selection_mode": "project",
                "kmitl_project_id": project.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "name": "Item",
                            "product_qty": 1.0,
                            "estimated_cost": cost,
                        },
                    )
                ],
            }
        )

    def _reserve(self, pr):
        pr.write({"state": "to_verify_budget"})
        pr.action_reserve_budget()

    def test_choosing_project_fills_budget_context(self):
        """Choosing the project writes its code, FY and full distribution
        (incl. its own kmitl_project dim) onto the พ.1 and its lines, locks the
        dims — and links no commitment until Reserve."""
        project = self._reserved_project()
        pr = self._make_pr(project)

        self.assertTrue(pr.use_project)
        self.assertEqual(pr.budget_account_id, self.budget_account)
        self.assertEqual(pr.account_fiscal_year_id, self.fiscal_year)
        self.assertEqual(pr.analytic_distribution, project.analytic_distribution)
        self.assertEqual(
            pr.line_ids.analytic_distribution, project.analytic_distribution
        )
        self.assertFalse(pr.is_budget_editable)
        self.assertTrue(pr.is_procurement_under_editable)
        self.assertFalse(pr.budget_commitment_id)

    def test_clearing_project_clears_budget_context(self):
        """Going back to งบประมาณปกติ drops the project and what it filled."""
        project = self._reserved_project()
        pr = self._make_pr(project)

        pr.write({"budget_selection_mode": "normal", "kmitl_project_id": False})

        self.assertFalse(pr.use_project)
        self.assertFalse(pr.budget_account_id)
        self.assertFalse(pr.analytic_distribution)

    def test_mode_alone_drops_project(self):
        """The mode is the answer: writing งบประมาณปกติ alone drops the project
        instead of being read back as "chose the project"."""
        project = self._reserved_project()
        pr = self._make_pr(project)

        pr.write({"budget_selection_mode": "normal"})

        self.assertEqual(pr.budget_selection_mode, "normal")
        self.assertFalse(pr.kmitl_project_id)
        self.assertFalse(pr.use_project)
        self.assertFalse(pr.budget_account_id)

    def test_copy_stays_under_project(self):
        project = self._reserved_project()
        pr = self._make_pr(project)

        copy = pr.copy()

        self.assertEqual(copy.budget_selection_mode, "project")
        self.assertEqual(copy.kmitl_project_id, project)
        self.assertTrue(copy.use_project)
        self.assertEqual(copy.budget_account_id, self.budget_account)

    def test_reserve_waits_for_project_approval(self):
        """A project whose หนังสือ is not signed yet (to_send) may be chosen, but
        Reserve refuses, naming the project's state."""
        project = self._reserved_project()
        pr = self._make_pr(project)

        with self.assertRaisesRegex(UserError, "ต้องรอให้โครงการ"):
            self._reserve(pr)

    def test_reserve_draws_project_commitment(self):
        """Once the project is approved, Reserve draws its single commitment and
        advances the พ.1; only then does it count against the headroom."""
        project = self._reserved_project()
        pr = self._make_pr(project, cost=1000.0)
        self.assertEqual(project._project_pr_total(), 0.0)
        self.assertEqual(pr.kmitl_project_remaining, project.budget_amount)

        project.action_approve()
        self._reserve(pr)

        self.assertNotEqual(pr.state, "to_verify_budget")
        self.assertEqual(pr.budget_commitment_id, project.budget_commitment_ids)
        self.assertEqual(project._project_pr_total(), 1000.0)

    def test_cap_counts_only_drawn_requests(self):
        """Undrawn พ.1 never hold headroom; a draw past the reserved amount is
        refused."""
        project = self._reserved_project(amount=1500.0)
        project.action_approve()
        first = self._make_pr(project, cost=1000.0)
        second = self._make_pr(project, cost=1000.0)

        self._reserve(first)
        with self.assertRaisesRegex(UserError, "เกินงบประมาณคงเหลือ"):
            self._reserve(second)

    def test_cancel_releases_headroom(self):
        """A cancelled พ.1 detaches from the project's commitment and stops
        counting."""
        project = self._reserved_project()
        project.action_approve()
        pr = self._make_pr(project, cost=1000.0)
        self._reserve(pr)

        # As the UI does: button_cancel only opens the wizard, which cancels.
        pr.button_cancel()
        self.env["purchase.request.cancel.wizard"].create(
            {"request_id": pr.id, "reason": "test"}
        ).action_confirm()

        self.assertEqual(pr.state, "cancelled")
        self.assertFalse(pr.budget_commitment_id)
        self.assertEqual(project._project_pr_total(), 0.0)

    def test_choice_locked_after_reserve(self):
        """After Reserve the project can no longer be changed, and ดึงกลับ
        (Reset) does not reopen it (budget ADR-0015)."""
        project = self._reserved_project()
        project.action_approve()
        pr = self._make_pr(project)
        self._reserve(pr)

        pr.button_draft()

        self.assertEqual(pr.state, "draft")
        self.assertEqual(pr.budget_commitment_id, project.budget_commitment_ids)
        self.assertFalse(pr.is_procurement_under_editable)
        # The view's readonly is bypassable over RPC; the server refuses too.
        # (uid 1 is always superuser, which the guard lets through.)
        user = self.env["res.users"].create(
            {
                "name": "PR Manager",
                "login": "pr_under_manager",
                "groups_id": [
                    (4, self.env.ref("base.group_user").id),
                    (
                        4,
                        self.env.ref(
                            "purchase_request.group_purchase_request_manager"
                        ).id,
                    ),
                ],
            }
        )
        if "operating_unit_id" in pr._fields and pr.operating_unit_id:
            user.operating_unit_ids = [(4, pr.operating_unit_id.id)]
        with self.assertRaisesRegex(UserError, "เปลี่ยน 'จัดซื้อภายใต้' ไม่ได้"):
            pr.with_user(user).write({"kmitl_project_id": False})

    def test_project_form_has_no_create_pr_action(self):
        """Every พ.1 starts on its own form: the project no longer creates one."""
        self.assertFalse(
            hasattr(self.env["kmitl.project"], "action_create_purchase_request")
        )
