# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentWorkflow(TransactionCase):
    """Post-bill payment-execution workflow: state machine + guards +
    the auditor's payment classification (subject / bank policy / method).

    The pre-bill approval (with budget) and the bill posting are exercised by
    finance_kmitl_demo; here we drive the round-2 states directly (writing the
    request to ``bills_posted``) to test the audit → authorize → paid chain in
    isolation — without a full chart of accounts.
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
        cls.partner_bank = cls.env["res.partner.bank"].create({
            "partner_id": cls.partner.id,
            "acc_number": "111-1-11111-1",
        })
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
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        if not cls.bank_journal:
            cls.bank_journal = cls.env["account.journal"].create({
                "name": "Bank Test", "type": "bank", "code": "BNKT",
                "company_id": cls.company.id,
            })
        cls.subject_fixed = cls.env["kmitl.payment.subject"].create({
            "name": "Test fixed subject",
            "bank_policy": "fixed",
            "journal_id": cls.bank_journal.id,
            "default_method": "transfer",
        })
        cls.subject_payee_bank = cls.env["kmitl.payment.subject"].create({
            "name": "Test payee-bank subject",
            "bank_policy": "payee_bank",
            "default_method": "transfer",
        })

    def _make_billed_request(self, classify=True, partner=None):
        """A request forced to ``bills_posted`` (round-2 entry point)."""
        partner = partner or self.partner
        request = self.env["disbursement.request"].create({
            "date": "2026-01-15",
            "partner_type": "multi",
            "analytic_distribution": self.distribution,
            "line_ids": [(0, 0, {
                "partner_id": partner.id,
                "product_id": self.product.id,
                "name": "Service",
                "quantity": 1,
                "price_unit": 1000.0,
                "account_id": self.expense_account.id,
                "analytic_distribution": self.distribution,
            })],
        })
        request.state = "bills_posted"
        if classify:
            request.payment_subject_id = self.subject_fixed
        return request

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def test_audit_authorize_forward(self):
        request = self._make_billed_request()
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")
        # Audit fills the line method from the subject default.
        self.assertEqual(request.line_ids.payment_method, "transfer")
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
        request = self._make_billed_request()
        request.action_audit()
        request.action_authorize()
        request.state = "paid"
        with self.assertRaises(UserError):
            request.action_cancel()

    # ------------------------------------------------------------------
    # Payment classification (audit validation)
    # ------------------------------------------------------------------
    def test_audit_requires_subject(self):
        request = self._make_billed_request(classify=False)
        with self.assertRaises(UserError):
            request.action_audit()

    def test_fixed_policy_requires_journal(self):
        subject = self.env["kmitl.payment.subject"].create({
            "name": "No journal", "bank_policy": "fixed",
            "default_method": "transfer",
        })
        request = self._make_billed_request(classify=False)
        request.payment_subject_id = subject
        with self.assertRaises(UserError):
            request.action_audit()

    def test_transfer_without_payee_bank_blocks(self):
        partner = self.env["res.partner"].create({"name": "No Bank Person"})
        request = self._make_billed_request(partner=partner)
        with self.assertRaisesRegex(UserError, "No Bank Person"):
            request.action_audit()

    def test_cheque_line_skips_bank_requirement(self):
        partner = self.env["res.partner"].create({"name": "Cheque Person"})
        request = self._make_billed_request(partner=partner)
        request.line_ids.payment_method = "cheque"
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")

    def test_mixed_methods_same_payee_blocks(self):
        request = self._make_billed_request()
        request.write({
            "line_ids": [(0, 0, {
                "partner_id": self.partner.id,
                "product_id": self.product.id,
                "name": "Second line",
                "quantity": 1,
                "price_unit": 500.0,
                "account_id": self.expense_account.id,
                "analytic_distribution": self.distribution,
            })],
        })
        request.line_ids[0].payment_method = "transfer"
        request.line_ids[1].payment_method = "cheque"
        with self.assertRaisesRegex(UserError, "Vendor A"):
            request.action_audit()

    def test_payee_bank_policy_resolves_matching_journal(self):
        bank = self.env["res.bank"].create({"name": "Match Bank"})
        company_account = self.env["res.partner.bank"].create({
            "partner_id": self.company.partner_id.id,
            "acc_number": "222-2-22222-2",
            "bank_id": bank.id,
        })
        journal = self.env["account.journal"].create({
            "name": "Match Bank Journal", "type": "bank", "code": "MBNK",
            "company_id": self.company.id,
            "bank_account_id": company_account.id,
        })
        self.partner_bank.bank_id = bank
        request = self._make_billed_request(classify=False)
        request.payment_subject_id = self.subject_payee_bank
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")
        self.assertEqual(
            request._resolve_line_journal(request.line_ids), journal
        )

    def test_payee_bank_policy_unmatched_blocks_with_name(self):
        other_bank = self.env["res.bank"].create({"name": "Elsewhere Bank"})
        self.partner_bank.bank_id = other_bank
        request = self._make_billed_request(classify=False)
        request.payment_subject_id = self.subject_payee_bank
        with self.assertRaisesRegex(UserError, "Vendor A"):
            request.action_audit()
