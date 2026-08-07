# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentWorkflow(TransactionCase):
    """Post-bill payment-execution workflow: state machine + guards.

    The pre-bill approval (with budget) and the bill posting are exercised by
    finance_kmitl_demo; here we drive the round-2 states directly (writing the
    request to ``bills_posted``) to test the audit → authorize → paid chain, its
    guards, and the revived pipeline status in isolation — without a full chart
    of accounts.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # The 4 required analytic dimensions so the request can leave draft.
        Plan = cls.env["account.analytic.plan"]
        Account = cls.env["account.analytic.account"]
        cls.distribution = {}
        for code in ("departments", "sources", "funds", "activities"):
            plan = Plan.search([("code", "=", code)], limit=1)
            if not plan:
                plan = Plan.create({"name": code.title(), "code": code})
            account = Account.create(
                {"name": "%s test" % code, "plan_id": plan.id}
            )
            cls.distribution[str(account.id)] = 100

        cls.partner = cls.env["res.partner"].create({"name": "Vendor A"})
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"),
             ("company_id", "=", cls.company.id)],
            limit=1,
        )
        if not cls.expense_account:
            cls.expense_account = cls.env["account.account"].create({
                "name": "Test Expense",
                "code": "TESTEXP",
                "account_type": "expense",
                "company_id": cls.company.id,
            })
        cls.product = cls.env["product.product"].create({
            "name": "Service", "type": "service",
        })

    def _make_billed_request(self):
        """A request forced to ``bills_posted`` (round-2 entry point)."""
        request = self.env["disbursement.request"].create({
            "date": "2026-01-15",
            "partner_type": "multi",
            "analytic_distribution": self.distribution,
            "line_ids": [(0, 0, {
                "partner_id": self.partner.id,
                "product_id": self.product.id,
                "name": "Service",
                "quantity": 1,
                "price_unit": 1000.0,
                "account_id": self.expense_account.id,
                "analytic_distribution": self.distribution,
            })],
        })
        request.state = "bills_posted"
        return request

    # ------------------------------------------------------------------
    def test_audit_authorize_forward(self):
        request = self._make_billed_request()
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")
        request.action_authorize()
        self.assertEqual(request.state, "payment_authorized")

    def test_audit_requires_bills_posted(self):
        request = self._make_billed_request()
        request.action_audit()  # -> payment_audited
        with self.assertRaises(UserError):
            request.action_audit()  # wrong source state

    def test_authorize_requires_audited(self):
        request = self._make_billed_request()
        with self.assertRaises(UserError):
            request.action_authorize()  # still bills_posted

    def test_confirm_paid_requires_payment(self):
        request = self._make_billed_request()
        request.action_audit()
        request.action_authorize()
        # No payment created yet -> cannot confirm as paid.
        with self.assertRaises(UserError):
            request.action_confirm_paid()

    def test_pipeline_done_when_cleared(self):
        # Revived pipeline (C1): a cleared request reports 'done' so the
        # "Done" filter and reporting work again.
        request = self._make_billed_request()
        request.state = "cleared"
        self.assertEqual(request.pipeline_status, "done")

    def test_cancel_blocked_after_audit_when_billed(self):
        # A billed request cannot be cancelled from the finance side once bills
        # are posted (the accounting bridge guard also applies).
        request = self._make_billed_request()
        request.action_audit()
        request.action_authorize()
        request.state = "paid"
        with self.assertRaises(UserError):
            request.action_cancel()
