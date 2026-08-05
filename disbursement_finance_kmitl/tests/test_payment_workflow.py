# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentWorkflow(TransactionCase):
    """Post-bill payment-execution workflow: state machine + guards + the
    auditor's classification (subject / paying account / method).

    The pre-bill approval (with budget) is exercised by finance_kmitl_demo; here
    we drive the round-2 states directly (writing the request to
    ``bills_posted``) to test the audit → authorize → paid chain in isolation.
    The bill itself is real, because a payment line is a payee-level row against
    a posted bill and reads its amount from it — faking the state without a bill
    would leave nothing to pay.
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

        # Minimum needed to post a vendor bill without a chart of accounts.
        cls.payable_account = cls.env["account.account"].search(
            [("account_type", "=", "liability_payable"),
             ("company_id", "=", cls.company.id)],
            limit=1,
        ) or cls.env["account.account"].create({
            "name": "Test Payable", "code": "TESTPAY",
            "account_type": "liability_payable",
            "reconcile": True, "company_id": cls.company.id,
        })
        cls.purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)],
            limit=1,
        ) or cls.env["account.journal"].create({
            "name": "Test Purchase", "code": "TPUR", "type": "purchase",
            "company_id": cls.company.id,
        })

        cls.transfer_type = cls.env.ref(
            "finance_kmitl.payment_type_normal_outbound"
        )
        cls.cheque_type = cls.env.ref(
            "finance_kmitl.payment_type_cheque_outbound"
        )

        # Paying accounts (หัวจ่าย): one per bank per method, as in the KMITL
        # chart. The KTB cheque account shares the bank account with the KTB
        # transfer account but books to its own GL.
        cls.paying_ktb = cls._make_paying_account(
            "PAYKTB", "ธ.กรุงไทย test", cls.ktb, "028-1-03878-3"
        )
        cls.paying_scb = cls._make_paying_account(
            "PAYSCB", "ธ.ไทยพาณิชย์ test", cls.scb, "088-2-11066-5"
        )
        cls.paying_ktb_cheque = cls._make_paying_account(
            "PAYKTBCQ", "เช็คจ่าย-ธ.กรุงไทย test", cls.ktb, None,
            payment_type=cls.cheque_type,
            bank_account=cls.paying_ktb.bank_account_id,
        )
        cls.subject_single = cls.env["kmitl.payment.subject"].create({
            "name": "Salary test",
            "default_payment_type_id": cls.transfer_type.id,
            "allowed_paying_account_ids": [(6, 0, cls.paying_ktb.ids)],
            "default_paying_account_id": cls.paying_ktb.id,
        })
        cls.subject_multi = cls.env["kmitl.payment.subject"].create({
            "name": "Advance test",
            "default_payment_type_id": cls.transfer_type.id,
            "auto_match_payee_bank": True,
            "allowed_paying_account_ids": [
                (6, 0, (cls.paying_ktb + cls.paying_scb).ids)
            ],
            "default_paying_account_id": cls.paying_ktb.id,
        })
        cls.subject_cheque = cls.env["kmitl.payment.subject"].create({
            "name": "Utilities test",
            "default_payment_type_id": cls.cheque_type.id,
            "allowed_paying_account_ids": [(6, 0, cls.paying_ktb_cheque.ids)],
            "default_paying_account_id": cls.paying_ktb_cheque.id,
        })

    @classmethod
    def _make_paying_account(cls, code, name, bank, acc_number,
                             payment_type=None, bank_account=None):
        """A หัวจ่าย: one of the institute's bank accounts paired with a method.

        The GL account belongs to the pair — a cheque drawn on the same bank
        account is booked elsewhere than a transfer — so each call makes its own.
        """
        gl_account = cls.env["account.account"].create({
            "name": name,
            "code": code,
            "account_type": "asset_cash",
            "company_id": cls.company.id,
        })
        bank_account = bank_account or cls.env["res.partner.bank"].create({
            "partner_id": cls.company.partner_id.id,
            "acc_number": acc_number,
            "bank_id": bank.id,
        })
        return cls.env["kmitl.paying.account"].create({
            "bank_account_id": bank_account.id,
            "payment_type_id": (payment_type or cls.transfer_type).id,
            "payment_account_id": gl_account.id,
            "company_id": cls.company.id,
        })

    def _make_bill(self, request, partner, partner_bank, amount):
        """A posted vendor bill for one payee, as the accounting bridge makes
        them (one bill per payee)."""
        partner.property_account_payable_id = self.payable_account
        bill = self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": partner.id,
            "partner_bank_id": partner_bank.id if partner_bank else False,
            "invoice_date": "2026-01-15",
            "date": "2026-01-15",
            "journal_id": self.purchase_journal.id,
            "disbursement_request_id": request.id,
            "invoice_line_ids": [(0, 0, {
                "name": "Service",
                "quantity": 1,
                "price_unit": amount,
                "account_id": self.expense_account.id,
                "tax_ids": [(6, 0, [])],
            })],
        })
        bill.action_post()
        return bill

    def _make_billed_request(self, subject=None, partner=None, bank=None):
        """A request forced to ``bills_posted`` (round-2 entry point), with its
        bill posted so the payment lines have something to be about."""
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
        self._make_bill(request, partner, partner_bank, 1000.0)
        # Entering bills_posted lays out the payee-level payment lines; the
        # subject is the auditor's decision, taken after that.
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
        self.assertEqual(
            request.payment_line_ids.payment_type_id, self.transfer_type
        )
        self.assertEqual(request.payment_line_ids.paying_account_id, self.paying_ktb)
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
            "name": "No account",
            "default_payment_type_id": self.transfer_type.id,
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
        self.assertEqual(request.payment_line_ids.paying_account_id, self.paying_scb)
        self.assertEqual(request.payment_line_ids.paying_account_match, "bank")

    def test_multi_account_subject_falls_back_to_default(self):
        other_bank = self.env["res.bank"].create({"name": "Elsewhere"})
        request = self._make_billed_request(
            subject=self.subject_multi, bank=other_bank
        )
        request.action_audit()
        self.assertEqual(request.payment_line_ids.paying_account_id, self.paying_ktb)
        # The line is flagged as fallen-to-fallback for the auditor to review.
        self.assertEqual(request.payment_line_ids.paying_account_match, "fallback")

    def test_no_auto_match_ignores_payee_bank(self):
        """With auto-match off the payee's bank is irrelevant: everyone pays
        from the main account, even when another allowed account matches."""
        subject = self.env["kmitl.payment.subject"].create({
            "name": "Fixed multi test",
            "default_payment_type_id": self.transfer_type.id,
            "auto_match_payee_bank": False,
            "allowed_paying_account_ids": [
                (6, 0, (self.paying_ktb + self.paying_scb).ids)
            ],
            "default_paying_account_id": self.paying_ktb.id,
        })
        request = self._make_billed_request(subject=subject, bank=self.scb)
        request.action_audit()
        self.assertEqual(request.payment_line_ids.paying_account_id, self.paying_ktb)
        self.assertEqual(request.payment_line_ids.paying_account_match, "main")

    def test_subject_change_keeps_manual_lines(self):
        """Re-deriving on a subject switch respects a hand-picked account."""
        request = self._make_billed_request(subject=self.subject_multi)
        request._apply_subject_defaults(request.payment_line_ids)
        line = request.payment_line_ids
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
        request._apply_subject_defaults(request.payment_line_ids)
        self.assertEqual(
            request.payment_line_ids.paying_account_id, self.paying_ktb
        )
        request.payment_subject_id = self.subject_single
        request._onchange_payment_subject_id()
        self.assertEqual(request.payment_line_ids.paying_account_id, self.paying_ktb)
        self.assertEqual(request.payment_line_ids.paying_account_match, "main")

    def test_account_outside_allowed_blocks(self):
        request = self._make_billed_request(subject=self.subject_single)
        request.payment_line_ids.paying_account_id = self.paying_scb
        with self.assertRaises(UserError):
            request.action_audit()

    def test_transfer_without_payee_bank_blocks(self):
        partner = self.env["res.partner"].create({"name": "No Bank Person"})
        request = self._make_billed_request(partner=partner)
        with self.assertRaisesRegex(UserError, "No Bank Person"):
            request.action_audit()

    def test_cheque_line_skips_bank_requirement(self):
        """A cheque is handed over, so the payee needs no bank account — and
        choosing the cheque paying account is what says so."""
        partner = self.env["res.partner"].create({"name": "Cheque Person"})
        request = self._make_billed_request(
            partner=partner, subject=self.subject_cheque
        )
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")
        self.assertEqual(
            request.payment_line_ids.paying_account_id, self.paying_ktb_cheque
        )

    # The two tests that checked a payee with mixed methods or mixed paying
    # accounts are gone: one payee is one payment line, so those are no longer
    # states the data can reach. See
    # docs/adr/0002-payee-level-payment-line.md.

    # ------------------------------------------------------------------
    # Paying account master data
    # ------------------------------------------------------------------
    def test_paying_account_gl_cannot_be_payable(self):
        """The money side may not be a receivable/payable account: Odoo tests it
        first when classifying the payment's lines and would swallow the
        counterpart. (That a paying account *has* a GL account is structural —
        the field is required — so only this needs a test.)"""
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.env["kmitl.paying.account"].create({
                "bank_account_id": self.paying_scb.bank_account_id.id,
                "payment_type_id": self.cheque_type.id,
                "payment_account_id": self.payable_account.id,
                "company_id": self.company.id,
            })

    def test_paying_account_is_unique_per_method(self):
        """The same bank account pairs with each method once — that uniqueness is
        what makes "which GL does a cheque on this account use" answerable."""
        from psycopg2 import IntegrityError

        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self._make_paying_account(
                "PAYKTBDUP", "ธ.กรุงไทย dup test", self.ktb, None,
                bank_account=self.paying_ktb.bank_account_id,
            )

    def test_subject_default_account_must_match_subject_method(self):
        """A cheque subject cannot fall back to a transfer account: it would pay
        the wrong way out of the wrong GL and nothing downstream would notice."""
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.env["kmitl.payment.subject"].create({
                "name": "Cheque subject with transfer fallback",
                "default_payment_type_id": self.cheque_type.id,
                "allowed_paying_account_ids": [(6, 0, self.paying_ktb.ids)],
                "default_paying_account_id": self.paying_ktb.id,
            })

    def test_subject_default_must_be_allowed(self):
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.env["kmitl.payment.subject"].create({
                "name": "Bad default",
                "default_payment_type_id": self.transfer_type.id,
                "allowed_paying_account_ids": [(6, 0, self.paying_ktb.ids)],
                "default_paying_account_id": self.paying_scb.id,
            })
