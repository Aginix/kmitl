# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentWorkflow(TransactionCase):
    """Post-bill payment-execution workflow: state machine + guards + the
    auditor's classification (subject / paying account / method).

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

        cls.ktb = cls.env["res.bank"].create({"name": "KTB test", "bic": "KRTHTHBK"})
        cls.scb = cls.env["res.bank"].create({"name": "SCB test", "bic": "SICOTHBK"})
        cls.partner = cls.env["res.partner"].create({"name": "Vendor A"})
        cls.partner_bank = cls.env["res.partner.bank"].create({
            "partner_id": cls.partner.id,
            "acc_number": "111-1-11111-1",
            "bank_id": cls.ktb.id,
        })
        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"),
             ("company_id", "=", cls.company.id)],
            limit=1,
        ) or cls.env["account.account"].create({
            "name": "Test Expense", "code": "TESTEXP",
            "account_type": "expense", "company_id": cls.company.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Service", "type": "service",
        })

        # Paying accounts (หัวจ่าย): one per bank, as in the KMITL chart.
        cls.paying_ktb = cls._make_paying_account(
            "PAYKTB", "ธ.กรุงไทย test", cls.ktb, "028-1-03878-3"
        )
        cls.paying_scb = cls._make_paying_account(
            "PAYSCB", "ธ.ไทยพาณิชย์ test", cls.scb, "088-2-11066-5"
        )
        cls.subject_single = cls.env["kmitl.payment.subject"].create({
            "name": "Salary test",
            "default_method": "transfer",
            "allowed_paying_account_ids": [(6, 0, cls.paying_ktb.ids)],
            "default_paying_account_id": cls.paying_ktb.id,
        })
        cls.subject_multi = cls.env["kmitl.payment.subject"].create({
            "name": "Advance test",
            "default_method": "transfer",
            "auto_match_payee_bank": True,
            "allowed_paying_account_ids": [
                (6, 0, (cls.paying_ktb + cls.paying_scb).ids)
            ],
            "default_paying_account_id": cls.paying_ktb.id,
        })

    @classmethod
    def _make_paying_account(cls, code, name, bank, acc_number):
        return cls.env["account.account"].create({
            "name": name,
            "code": code,
            "account_type": "asset_cash",
            "company_id": cls.company.id,
            "is_paying_account": True,
            "paying_bank_id": bank.id,
            "paying_acc_number": acc_number,
        })

    def _make_billed_request(self, subject=None, partner=None, bank=None):
        """A request forced to ``bills_posted`` (round-2 entry point)."""
        partner = partner or self.partner
        partner_bank = self.partner_bank if partner == self.partner else False
        if bank is not None and partner_bank:
            partner_bank.bank_id = bank
        request = self.env["disbursement.request"].create({
            "date": "2026-01-15",
            "partner_type": "multi",
            "analytic_distribution": self.distribution,
            "line_ids": [(0, 0, {
                "partner_id": partner.id,
                "partner_bank_id": partner_bank.id if partner_bank else False,
                "product_id": self.product.id,
                "name": "Service",
                "quantity": 1,
                "price_unit": 1000.0,
                "account_id": self.expense_account.id,
                "analytic_distribution": self.distribution,
            })],
        })
        request.state = "bills_posted"
        request.payment_subject_id = subject or self.subject_single
        return request

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def test_audit_authorize_forward(self):
        request = self._make_billed_request()
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")
        # The audit fills method and paying account from the subject.
        self.assertEqual(request.line_ids.payment_method, "transfer")
        self.assertEqual(request.line_ids.paying_account_id, self.paying_ktb)
        request.action_authorize()
        self.assertEqual(request.state, "payment_authorized")

    def test_audit_requires_bills_posted(self):
        request = self._make_billed_request()
        request.action_audit()
        with self.assertRaises(UserError):
            request.action_audit()

    def test_authorize_requires_audited(self):
        request = self._make_billed_request()
        with self.assertRaises(UserError):
            request.action_authorize()

    def test_confirm_paid_requires_payment(self):
        request = self._make_billed_request()
        request.action_audit()
        request.action_authorize()
        with self.assertRaises(UserError):
            request.action_confirm_paid()

    def test_pipeline_done_when_cleared(self):
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
        request = self._make_billed_request()
        request.payment_subject_id = False
        with self.assertRaises(UserError):
            request.action_audit()

    def test_subject_with_no_account_blocks(self):
        subject = self.env["kmitl.payment.subject"].create({
            "name": "No account", "default_method": "transfer",
        })
        request = self._make_billed_request(subject=subject)
        with self.assertRaisesRegex(UserError, "Vendor A"):
            request.action_audit()

    def test_multi_account_subject_picks_payee_bank(self):
        """Auto-match serves each payee from the account held at their own
        bank, and records the match so the auditor can see it."""
        request = self._make_billed_request(
            subject=self.subject_multi, bank=self.scb
        )
        request.action_audit()
        self.assertEqual(request.line_ids.paying_account_id, self.paying_scb)
        self.assertEqual(request.line_ids.paying_account_match, "bank")

    def test_multi_account_subject_falls_back_to_default(self):
        other_bank = self.env["res.bank"].create({"name": "Elsewhere"})
        request = self._make_billed_request(
            subject=self.subject_multi, bank=other_bank
        )
        request.action_audit()
        self.assertEqual(request.line_ids.paying_account_id, self.paying_ktb)
        # The line is flagged as fallen-to-fallback for the auditor to review.
        self.assertEqual(request.line_ids.paying_account_match, "fallback")

    def test_no_auto_match_ignores_payee_bank(self):
        """With auto-match off the payee's bank is irrelevant: everyone pays
        from the main account, even when another allowed account matches."""
        subject = self.env["kmitl.payment.subject"].create({
            "name": "Fixed multi test",
            "default_method": "transfer",
            "auto_match_payee_bank": False,
            "allowed_paying_account_ids": [
                (6, 0, (self.paying_ktb + self.paying_scb).ids)
            ],
            "default_paying_account_id": self.paying_ktb.id,
        })
        request = self._make_billed_request(subject=subject, bank=self.scb)
        request.action_audit()
        self.assertEqual(request.line_ids.paying_account_id, self.paying_ktb)
        self.assertEqual(request.line_ids.paying_account_match, "main")

    def test_subject_change_keeps_manual_lines(self):
        """Re-deriving on a subject switch respects a hand-picked account."""
        request = self._make_billed_request(subject=self.subject_multi)
        request._apply_subject_defaults(request.line_ids)
        line = request.line_ids
        line.write({
            "paying_account_id": self.paying_scb.id,
            "paying_account_match": "manual",
        })
        request.payment_subject_id = self.subject_single
        request._onchange_payment_subject_id()
        self.assertEqual(line.paying_account_id, self.paying_scb)
        self.assertEqual(line.paying_account_match, "manual")

    def test_subject_change_rederives_derived_lines(self):
        request = self._make_billed_request(subject=self.subject_multi)
        request._apply_subject_defaults(request.line_ids)
        self.assertEqual(
            request.line_ids.paying_account_id, self.paying_ktb
        )
        request.payment_subject_id = self.subject_single
        request._onchange_payment_subject_id()
        self.assertEqual(request.line_ids.paying_account_id, self.paying_ktb)
        self.assertEqual(request.line_ids.paying_account_match, "main")

    def test_account_outside_allowed_blocks(self):
        request = self._make_billed_request(subject=self.subject_single)
        request.line_ids.paying_account_id = self.paying_scb
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
                "partner_bank_id": self.partner_bank.id,
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

    def test_mixed_paying_accounts_same_payee_blocks(self):
        request = self._make_billed_request(subject=self.subject_multi)
        request.write({
            "line_ids": [(0, 0, {
                "partner_id": self.partner.id,
                "partner_bank_id": self.partner_bank.id,
                "product_id": self.product.id,
                "name": "Second line",
                "quantity": 1,
                "price_unit": 500.0,
                "account_id": self.expense_account.id,
                "analytic_distribution": self.distribution,
            })],
        })
        request.line_ids[0].paying_account_id = self.paying_ktb
        request.line_ids[1].paying_account_id = self.paying_scb
        with self.assertRaisesRegex(UserError, "Vendor A"):
            request.action_audit()

    # ------------------------------------------------------------------
    # Paying account master data
    # ------------------------------------------------------------------
    def test_paying_account_at_bank_needs_number(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.env["account.account"].create({
                "name": "Bank no number", "code": "PAYNONUM",
                "account_type": "asset_cash", "company_id": self.company.id,
                "is_paying_account": True, "paying_bank_id": self.ktb.id,
            })

    def test_subject_default_must_be_allowed(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.env["kmitl.payment.subject"].create({
                "name": "Bad default",
                "default_method": "transfer",
                "allowed_paying_account_ids": [(6, 0, self.paying_ktb.ids)],
                "default_paying_account_id": self.paying_scb.id,
            })
