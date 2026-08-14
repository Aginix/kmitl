# -*- coding: utf-8 -*-
from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestCreatePrFromProject(TransactionCase):
    """The 'สร้างใบขอซื้อ' action on kmitl.project pre-fills a purchase.request from
    the project's reserved-budget context (ADR-0007) — process mirroring the
    procurement plan, without a procurement method (each PR picks its own)."""

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

        cls.budget_account = env["budget.account"].create(
            {
                "code": "TESTPRJ010",
                "name": "Test Project Code",
                "budget_type": "expense",
                "budgetable": True,
                "is_project": True,
                "project_type": "project",
            }
        )

    def _make_project(self, amount=100000.0):
        return self.env["kmitl.project"].create(
            {
                "name": "Test Project",
                "project_type": "project",
                "account_fiscal_year_id": self.fiscal_year.id,
                "budget_account_id": self.budget_account.id,
                "budget_amount": amount,
            }
        )

    def _approve_project(self, project):
        """Walk the approval-gated lifecycle (kmitl_project ADR-0005) up to the
        executing state a พ.1 may be raised from: ยืนยัน → จองงบประมาณ → อนุมัติ
        (the manual fallback used when kmitl_project_sarabun is not installed)."""
        project.action_confirm()
        project.action_reserve_budget()
        project.action_approve()
        return project

    def test_button_hidden_until_approved(self):
        """can_create_purchase_request is False in draft and while the project is
        only reserved (to_send); it turns True once the project is approved."""
        project = self._make_project()
        self.assertFalse(project.can_create_purchase_request)
        project.action_confirm()
        project.action_reserve_budget()
        self.assertEqual(project.state, "to_send")
        self.assertFalse(project.can_create_purchase_request)
        project.action_approve()
        self.assertTrue(project.can_create_purchase_request)

    def test_action_requires_reservation(self):
        """Creating a PR from an unreserved (draft) project is blocked."""
        project = self._make_project()
        with self.assertRaises(UserError):
            project.action_create_purchase_request()

    def test_action_requires_approval(self):
        """A reserved but not-yet-approved project (to_send) cannot raise a พ.1 —
        the ขออนุมัติ หนังสือ must be signed first (ADR-0005)."""
        project = self._make_project()
        project.action_confirm()
        project.action_reserve_budget()
        with self.assertRaises(UserError):
            project.action_create_purchase_request()

    def test_action_prefill_context(self):
        """The action pre-fills the PR from the project and links its shared
        commitment — and does NOT prefill a procurement method."""
        project = self._approve_project(self._make_project())
        commitment = project.budget_commitment_ids

        action = project.action_create_purchase_request()
        ctx = action["context"]

        self.assertEqual(action["res_model"], "purchase.request")
        self.assertTrue(ctx["default_use_project"])
        self.assertEqual(ctx["default_kmitl_project_id"], project.id)
        self.assertEqual(ctx["default_budget_commitment_id"], commitment.id)
        self.assertEqual(ctx["default_budget_account_id"], self.budget_account.id)
        self.assertEqual(
            ctx["default_account_fiscal_year_id"], self.fiscal_year.id
        )
        self.assertEqual(ctx["default_title"], project.name)
        # The full project analytic distribution (incl. its kmitl_project dimension)
        # is prefilled so spend is attributed back to the project.
        self.assertEqual(
            ctx["default_analytic_distribution"], project.analytic_distribution
        )
        # Projects carry no procurement method — each PR chooses its own.
        self.assertNotIn("default_procurement_method_id", ctx)
