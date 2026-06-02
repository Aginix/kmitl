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

    def test_button_hidden_until_reserved(self):
        """can_create_purchase_request is False in draft, True once reserved."""
        project = self._make_project()
        self.assertFalse(project.can_create_purchase_request)
        project.button_new()
        self.assertTrue(project.can_create_purchase_request)

    def test_action_requires_reservation(self):
        """Creating a PR from an unreserved (draft) project is blocked."""
        project = self._make_project()
        with self.assertRaises(UserError):
            project.action_create_purchase_request()

    def test_action_prefill_context(self):
        """The action pre-fills the PR from the project and links its shared
        commitment — and does NOT prefill a procurement method."""
        project = self._make_project()
        project.button_new()
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
        # Projects carry no procurement method — each PR chooses its own.
        self.assertNotIn("default_procurement_method_id", ctx)
