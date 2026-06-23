# -*- coding: utf-8 -*-
from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLinkToPlan(TransactionCase):
    """A plan-driven purchase request must receive the procurement plan's FULL
    analytic_distribution (not a single analytic dimension) and budget context
    server-side via _link_to_procurement_plan, so the value survives even though
    purchase.request.analytic_distribution is a core field with a no-op compute
    that the live-form onchange cannot prefill reliably."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        env["ir.config_parameter"].sudo().set_param("budget.allow_negative", "True")

        cls.activity_account = env["account.analytic.account"].create(
            {
                "name": "Test Activity",
                "plan_id": env.ref(
                    "account_analytic_kmitl.analytic_plan_activities"
                ).id,
            }
        )
        cls.source_account = env["account.analytic.account"].create(
            {
                "name": "Test Source",
                "plan_id": env.ref(
                    "account_analytic_kmitl.analytic_plan_sources"
                ).id,
            }
        )

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
                "code": "TESTPPLINK",
                "name": "Test Procurement Plan Code",
                "budget_type": "expense",
                "budgetable": True,
            }
        )
        cls.method = env["procurement.method"].create({"name": "Test Method"})

    def _make_ready_plan(self):
        plan = self.env["procurement.plan"].create(
            {
                "description": "Test Plan",
                "amount": 1,
                "unit": "ชุด",
                "total_price": 1000.0,
                "account_fiscal_year_id": self.fiscal_year.id,
                "budget_account_id": self.budget_account.id,
                "procurement_method_id": self.method.id,
                "purchase_request_eta": "1",
                "procurement_announcement_eta": "2",
                "approval_signing_eta": "3",
                "contract_order_signing_eta": "4",
                "acceptance_eta": "5",
                "analytic_distribution": {
                    str(self.activity_account.id): 100,
                    str(self.source_account.id): 100,
                },
            }
        )
        plan.action_new()
        plan.action_ready()
        return plan

    def test_link_copies_full_distribution_server_side(self):
        """The whole plan distribution (financial dims + the plan's own
        procurement_plan dimension) is written onto the PR — not rebuilt from a
        single analytic_id."""
        plan = self._make_ready_plan()
        # The plan carries its own procurement_plan dimension on top of the two
        # financial dims, so the distribution has more than one entry to copy.
        self.assertIn(
            str(plan.analytic_account_id.id), plan.analytic_distribution
        )

        pr = self.env["purchase.request"].create(
            {
                "use_procurement_plan": True,
                "procurement_plan_id": plan.id,
            }
        )

        self.assertEqual(
            pr.analytic_distribution,
            plan.analytic_distribution,
            "the PR must receive the plan's full analytic_distribution",
        )
        self.assertEqual(pr.budget_account_id, plan.budget_account_id)
        self.assertEqual(pr.account_fiscal_year_id, plan.account_fiscal_year_id)
        self.assertEqual(pr.procurement_method_id, plan.procurement_method_id)

    def test_link_attaches_shared_commitment(self):
        """The PR links the plan's already-reserved shared commitment."""
        plan = self._make_ready_plan()
        commitment = plan.budget_commitment_ids.filtered(
            lambda c: c.state in ("reserved", "partial")
        )[:1]
        self.assertTrue(commitment)

        pr = self.env["purchase.request"].create(
            {
                "use_procurement_plan": True,
                "procurement_plan_id": plan.id,
            }
        )
        self.assertEqual(pr.budget_commitment_id, commitment)
