from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProcurementUnderPlan(TransactionCase):
    """A พ.1 names the แผนจัดซื้อจัดจ้าง it is bought under on its own form
    (จัดซื้อภายใต้, root ADR-0011): choosing the plan claims it (1 แผน = 1 พ.1)
    and fills its budget context; the plan starts only at Reserve, and a
    cancelled or rejected พ.1 gives it back."""

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
        cls.product = env["product.product"].create(
            {"name": "Test Plan Product", "type": "consu"}
        )
        cls.budget_account = env["budget.account"].create(
            {
                "code": "TESTPLANPR01",
                "name": "Test Plan Code",
                "budget_type": "expense",
                "budgetable": True,
                "procurement_plan": True,
                "purchase_ok": True,
                "product_id": cls.product.id,
            }
        )

    def _verified_plan(self, with_commitment=False):
        plan = self.env["procurement.plan"].create(
            {
                "description": "Test Plan",
                "amount": 1,
                "unit": "ชุด",
                "total_price": 5000.0,
                "account_fiscal_year_id": self.fiscal_year.id,
                "budget_account_id": self.budget_account.id,
            }
        )
        plan.write({"state": "verified"})
        if with_commitment:
            commitment = self.env["budget.commitment"].create(
                {
                    "amount": 5000.0,
                    "account_id": self.budget_account.id,
                    "account_fiscal_year_id": self.fiscal_year.id,
                    "procurement_plan_id": plan.id,
                }
            )
            commitment.action_reserve()
        return plan

    def _make_pr(self, plan=None):
        vals = {
            "title": "Test PR",
            "requested_by": self.env.ref("base.user_admin").id,
            "account_fiscal_year_id": self.fiscal_year.id,
        }
        if plan:
            vals.update(
                {
                    "budget_selection_mode": "procurement_plan",
                    "procurement_plan_id": plan.id,
                }
            )
        return self.env["purchase.request"].create(vals)

    def _cancel(self, pr):
        # As the UI does: button_cancel only opens the wizard, which cancels.
        pr.button_cancel()
        self.env["purchase.request.cancel.wizard"].create(
            {"request_id": pr.id, "reason": "test"}
        ).action_confirm()

    def _offered(self, pr):
        return self.env["procurement.plan"].search(pr.procurement_plan_domain)

    def test_choosing_plan_fills_context_without_starting_it(self):
        plan = self._verified_plan()
        pr = self._make_pr(plan)

        self.assertTrue(pr.use_procurement_plan)
        self.assertEqual(pr.budget_account_id, self.budget_account)
        self.assertEqual(pr.account_fiscal_year_id, self.fiscal_year)
        self.assertFalse(pr.is_budget_editable)
        self.assertFalse(pr.budget_commitment_id)
        # Claimed, but not started: the plan moves only at Reserve.
        self.assertEqual(plan.state, "verified")

    def test_plan_claimed_when_chosen(self):
        """A second พ.1 can neither be offered nor take the plan another live
        พ.1 already holds."""
        plan = self._verified_plan()
        self._make_pr(plan)

        other = self._make_pr()
        self.assertNotIn(plan, self._offered(other))
        with self.assertRaisesRegex(UserError, "1 แผน ต่อ 1 ใบขอซื้อ"):
            self._make_pr(plan)

    def test_plan_offered_only_in_request_fiscal_year(self):
        plan = self._verified_plan()
        other_year = self.env["account.fiscal.year"].create(
            {
                "name": "FY-TEST-OTHER",
                "date_from": date(2090, 10, 1),
                "date_to": date(2091, 9, 30),
                "company_id": self.env.company.id,
            }
        )
        pr = self._make_pr()
        self.assertIn(plan, self._offered(pr))

        pr.account_fiscal_year_id = other_year
        self.assertNotIn(plan, self._offered(pr))

    def test_cancel_releases_claim(self):
        plan = self._verified_plan()
        first = self._make_pr(plan)
        self._cancel(first)

        other = self._make_pr()
        self.assertIn(plan, self._offered(other))
        self._make_pr(plan)

    def test_reserve_starts_plan(self):
        """Reserve draws the plan's single commitment and starts the plan; a
        cancelled drawn พ.1 returns the plan to verified."""
        plan = self._verified_plan(with_commitment=True)
        pr = self._make_pr(plan)
        pr.write({"state": "to_verify_budget"})

        pr.action_reserve_budget()

        self.assertEqual(pr.budget_commitment_id, plan.budget_commitment_ids)
        self.assertEqual(plan.state, "in_progress")

        self._cancel(pr)

        self.assertFalse(pr.budget_commitment_id)
        self.assertEqual(plan.state, "verified")

    def test_copy_does_not_claim_plan(self):
        plan = self._verified_plan()
        pr = self._make_pr(plan)

        copy = pr.copy()

        self.assertFalse(copy.procurement_plan_id)
        self.assertFalse(copy.use_procurement_plan)
        self.assertFalse(copy.budget_account_id)
        self.assertFalse(copy.analytic_distribution)
