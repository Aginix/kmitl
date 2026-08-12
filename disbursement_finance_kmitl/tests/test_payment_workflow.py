# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from lxml import etree

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentWorkflow(TransactionCase):
    """Post-bill payment-execution workflow: state machine, guards, and the
    payee-level paying account.

    The pre-bill approval (with budget) is exercised by ``finance_kmitl_demo``;
    here the bills are made directly and posted, which is what carries the
    request into ``bills_posted`` and makes the payment lines.
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
            account = Account.create({"name": "%s test" % code, "plan_id": plan.id})
            cls.distribution[str(account.id)] = 100

        cls.expense_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.payable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.purchase_journal = cls.env.ref("account_kmitl.journal_ap")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Service",
                "type": "service",
            }
        )

        # Seeded paying accounts (หัวจ่าย) on ใบสำคัญจ่าย.
        cls.scb_account = cls.env.ref(
            "account_kmitl.paying_account_1112210004_transfer"
        )
        cls.ktb_account = cls.env.ref(
            "account_kmitl.paying_account_1112120002_transfer"
        )
        cls.cheque_account = cls.env.ref(
            "account_kmitl.paying_account_1112220015_cheque"
        )
        cls.cash_account = cls.env.ref("account_kmitl.paying_account_1111000002_cash")

        cls.subject_vendor = cls.env.ref("finance_kmitl.payment_subject_vendor_direct")
        cls.subject_advance = cls.env.ref(
            "finance_kmitl.payment_subject_advance_reimburse"
        )

        # A payee banking with KTB, and one banking nowhere the institute does.
        cls.payee_ktb = cls._make_payee("Payee KTB", cls.ktb_account.bank_id)
        other_bank = cls.env["res.bank"].create(
            {"name": "Some Other Bank", "bic": "OTHRTHBK"}
        )
        cls.payee_other = cls._make_payee("Payee Other", other_bank)

    @classmethod
    def _make_payee(cls, name, bank):
        partner = cls.env["res.partner"].create(
            {
                "name": name,
                "property_account_payable_id": cls.payable_account.id,
            }
        )
        cls.env["res.partner.bank"].create(
            {
                "partner_id": partner.id,
                "acc_number": "TEST-%s" % name.replace(" ", "-"),
                "bank_id": bank.id,
            }
        )
        return partner

    # ------------------------------------------------------------------
    def _make_request(self, payees=None):
        payees = payees or [self.payee_ktb]
        return self.env["disbursement.request"].create(
            {
                "date": "2026-01-15",
                "partner_type": "multi",
                "analytic_distribution": self.distribution,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "partner_id": payee.id,
                            "product_id": self.product.id,
                            "name": "Service",
                            "quantity": 1,
                            "price_unit": 1000.0,
                            "account_id": self.expense_account.id,
                            "analytic_distribution": self.distribution,
                        },
                    )
                    for payee in payees
                ],
            }
        )

    def _post_bills(self, request, payees):
        """Post one vendor bill per payee, which carries the request into
        ``bills_posted`` exactly as the accounting bridge does in production."""
        request.state = "approved"
        for payee in payees:
            bill = self.env["account.move"].create(
                {
                    "move_type": "in_invoice",
                    "partner_id": payee.id,
                    "partner_bank_id": payee.bank_ids[:1].id,
                    "invoice_date": "2026-01-15",
                    "journal_id": self.purchase_journal.id,
                    "disbursement_request_id": request.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": "Service",
                                "quantity": 1,
                                "price_unit": 1000.0,
                                "account_id": self.expense_account.id,
                                "analytic_distribution": self.distribution,
                            },
                        )
                    ],
                }
            )
            bill.action_post()
        self.assertEqual(request.state, "bills_posted")
        return request

    def _billed_request(self, payees=None, subject=None):
        payees = payees or [self.payee_ktb]
        request = self._make_request(payees)
        self._post_bills(request, payees)
        request.payment_subject_id = subject or self.subject_vendor
        return request

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------
    def test_paying_accounts_are_seeded_with_their_bank(self):
        journal = self.env.ref("account_kmitl.journal_pv")
        paying = journal.outbound_payment_method_line_ids.filtered("payment_account_id")
        self.assertEqual(len(paying), 8)
        banked = paying.filtered(lambda a: a.payment_method_id.code != "kmitl_cash")
        self.assertTrue(all(banked.mapped("bank_account_id")))
        # And each of those bank accounts resolved to a bank: without it
        # auto-matching a payee's own bank can never match and the e-payment
        # file names no sending bank.
        self.assertTrue(all(banked.mapped("bank_id")))
        self.assertEqual(self.ktb_account.bank_id.bic, "KRTHTHBK")
        self.assertEqual(self.scb_account.bank_id.bic, "SICOTHBK")
        # Cash books against cash on hand, not against a bank.
        self.assertFalse(self.cash_account.bank_account_id)
        self.assertEqual(self.cash_account.payment_account_id.code, "1111000002")

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def test_audit_authorize_forward(self):
        request = self._billed_request()
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")
        request.action_authorize()
        self.assertEqual(request.state, "payment_authorized")

    def test_audit_requires_bills_posted(self):
        request = self._billed_request()
        request.action_audit()  # -> payment_audited
        with self.assertRaises(UserError):
            request.action_audit()  # wrong source state

    def test_authorize_requires_audited(self):
        request = self._billed_request()
        with self.assertRaises(UserError):
            request.action_authorize()  # still bills_posted

    def test_confirm_paid_requires_payment(self):
        request = self._billed_request()
        request.action_audit()
        request.action_authorize()
        with self.assertRaises(UserError):
            request.action_confirm_paid()

    def test_pipeline_done_when_cleared(self):
        request = self._billed_request()
        request.state = "cleared"
        self.assertEqual(request.pipeline_status, "done")

    def test_cancel_blocked_after_audit_when_billed(self):
        request = self._billed_request()
        request.action_audit()
        request.action_authorize()
        request.state = "paid"
        with self.assertRaises(UserError):
            request.action_cancel()

    # ------------------------------------------------------------------
    # Payment lines
    # ------------------------------------------------------------------
    def test_one_payment_line_per_payee(self):
        request = self._billed_request([self.payee_ktb, self.payee_other])
        self.assertEqual(len(request.payment_line_ids), 2)
        self.assertEqual(
            request.payment_line_ids.mapped("partner_id"),
            self.payee_ktb + self.payee_other,
        )

    def test_ensure_payment_lines_is_idempotent(self):
        request = self._billed_request()
        request._ensure_payment_lines()
        request._ensure_payment_lines()
        self.assertEqual(len(request.payment_line_ids), 1)

    def test_amounts_come_from_the_bill(self):
        request = self._billed_request()
        line = request.payment_line_ids
        self.assertEqual(line.amount_bill, 1000.0)
        self.assertEqual(line.amount_net, 1000.0 - line.amount_wht)

    # ------------------------------------------------------------------
    # Paying account derivation
    # ------------------------------------------------------------------
    def test_fixed_subject_pays_everyone_from_the_main_account(self):
        request = self._billed_request(
            [self.payee_ktb, self.payee_other], self.subject_vendor
        )
        lines = request.payment_line_ids
        self.assertEqual(
            set(lines.mapped("paying_account_id").ids), {self.scb_account.id}
        )
        self.assertEqual(set(lines.mapped("paying_account_match")), {"main"})

    def test_auto_match_serves_a_payee_from_their_own_bank(self):
        request = self._billed_request(
            [self.payee_ktb, self.payee_other], self.subject_advance
        )
        by_payee = {line.partner_id: line for line in request.payment_line_ids}
        self.assertEqual(by_payee[self.payee_ktb].paying_account_id, self.ktb_account)
        self.assertEqual(by_payee[self.payee_ktb].paying_account_match, "bank")
        # Nobody banks there: falls back to the subject's account.
        self.assertEqual(by_payee[self.payee_other].paying_account_id, self.scb_account)
        self.assertEqual(by_payee[self.payee_other].paying_account_match, "fallback")

    def test_a_hand_picked_account_survives_re_derivation(self):
        request = self._billed_request([self.payee_ktb], self.subject_advance)
        line = request.payment_line_ids
        line.write(
            {
                "paying_account_id": self.cheque_account.id,
                "paying_account_match": "manual",
            }
        )
        request.payment_subject_id = self.subject_vendor
        self.assertEqual(line.paying_account_id, self.cheque_account)
        self.assertEqual(line.paying_account_match, "manual")

    def test_method_follows_the_paying_account(self):
        request = self._billed_request([self.payee_ktb], self.subject_advance)
        line = request.payment_line_ids
        line.paying_account_id = self.cheque_account
        self.assertEqual(line.payment_method_id.code, "kmitl_cheque")

    # ------------------------------------------------------------------
    # Deriving in the form (the auditor picks the subject)
    # ------------------------------------------------------------------
    def _unsaved_form(self, request, subject):
        """``request`` as an open form on which the subject has just been
        picked: a new record with the saved one as its origin, which is exactly
        what ``onchange`` hands the method for the client."""
        return request.new(
            {
                "state": request.state,
                "payment_subject_id": subject.id,
                "payment_line_ids": [
                    (4, line.id, 0) for line in request.payment_line_ids
                ],
            },
            origin=request,
        )

    def test_picking_the_subject_fills_the_rows_before_saving(self):
        payees = [self.payee_ktb, self.payee_other]
        request = self._make_request(payees)
        self._post_bills(request, payees)
        form = self._unsaved_form(request, self.subject_advance)
        form._onchange_payment_subject_id()
        shown = {
            line.partner_id: (line.paying_account_id, line.paying_account_match)
            for line in form.payment_line_ids
        }
        self.assertEqual(shown[self.payee_ktb], (self.ktb_account, "bank"))
        self.assertEqual(shown[self.payee_other], (self.scb_account, "fallback"))
        # An onchange fills the form in; it writes nothing.
        self.assertFalse(request.payment_subject_id)
        self.assertFalse(request.payment_line_ids.mapped("paying_account_id"))

    def test_the_form_leaves_a_hand_picked_row_alone(self):
        request = self._billed_request([self.payee_ktb], self.subject_advance)
        request.payment_line_ids.write(
            {
                "paying_account_id": self.cheque_account.id,
                "paying_account_match": "manual",
            }
        )
        form = self._unsaved_form(request, self.subject_vendor)
        form._onchange_payment_subject_id()
        line = form.payment_line_ids
        self.assertEqual(line.paying_account_id, self.cheque_account)
        self.assertEqual(line.paying_account_match, "manual")

    def test_the_provenance_of_a_row_survives_the_save(self):
        """``paying_account_match`` is readonly, and the web client drops
        readonly fields from a save. Without ``force_save`` the "chosen by hand"
        that the row reports while the form is open would never reach the
        database, and the re-derivation that runs in the same save would
        overwrite the account the person just picked."""
        arch = etree.fromstring(self.env["disbursement.request"].get_view()["arch"])
        match = arch.xpath(
            "//field[@name='payment_line_ids']//field[@name='paying_account_match']"
        )
        self.assertTrue(match, "the provenance column belongs in the audit rows")
        self.assertTrue(match[0].get("force_save"))

    # ------------------------------------------------------------------
    # Audit guards
    # ------------------------------------------------------------------
    def test_audit_needs_a_subject(self):
        payees = [self.payee_ktb]
        request = self._make_request(payees)
        self._post_bills(request, payees)
        with self.assertRaises(UserError):
            request.action_audit()

    def test_audit_refuses_a_transfer_payee_without_a_bank_account(self):
        payee = self.env["res.partner"].create(
            {
                "name": "Bankless",
                "property_account_payable_id": self.payable_account.id,
            }
        )
        payees = [payee]
        request = self._make_request(payees)
        self._post_bills(request, payees)
        request.payment_subject_id = self.subject_vendor
        with self.assertRaises(UserError):
            request.action_audit()
        # Moving them onto cash unblocks it — cash needs no bank account.
        request.payment_line_ids.write(
            {
                "paying_account_id": self.cash_account.id,
                "paying_account_match": "manual",
            }
        )
        request.action_audit()
        self.assertEqual(request.state, "payment_audited")

    # ------------------------------------------------------------------
    # Payment creation
    # ------------------------------------------------------------------
    def test_payment_carries_the_paying_account_and_its_voucher(self):
        request = self._billed_request(
            [self.payee_ktb, self.payee_other], self.subject_advance
        )
        request.action_audit()
        request.action_authorize()
        request.action_create_payment()
        by_payee = {p.partner_id: p for p in request.payment_ids}
        self.assertEqual(
            by_payee[self.payee_ktb].payment_method_line_id, self.ktb_account
        )
        self.assertEqual(
            by_payee[self.payee_ktb].journal_id, self.ktb_account.journal_id
        )
        self.assertEqual(
            by_payee[self.payee_other].payment_method_line_id, self.scb_account
        )
        self.assertEqual(
            request.payment_line_ids.mapped("payment_id"), request.payment_ids
        )

    def test_banking_coordinates_freeze_once_the_payment_exists(self):
        request = self._billed_request([self.payee_ktb], self.subject_vendor)
        request.action_audit()
        request.action_authorize()
        request.action_create_payment()
        with self.assertRaises(UserError):
            request.payment_line_ids.paying_account_id = self.ktb_account

    # ------------------------------------------------------------------
    # Two lifecycles on one voucher (ADR-0005)
    # ------------------------------------------------------------------
    def _authorized_with_payments(self, paying_account=None):
        """A request whose payments exist and are still the finance office's."""
        request = self._billed_request([self.payee_ktb], self.subject_vendor)
        if paying_account:
            request.payment_line_ids.write(
                {
                    "paying_account_id": paying_account.id,
                    "paying_account_match": "manual",
                }
            )
        request.action_audit()
        request.action_authorize()
        request.action_create_payment()
        return request

    def test_confirming_for_the_bank_leaves_the_accounting_status_alone(self):
        request = self._authorized_with_payments()
        payment = request.payment_ids
        payment.action_confirm_for_bank()
        # Numbered and frozen, which is what an e-payment file needs...
        self.assertEqual(payment.finance_state, "confirmed")
        self.assertTrue(payment.name and payment.name != "/")
        # ...and still the accounting office's untouched draft.
        self.assertEqual(payment.state, "draft")
        self.assertEqual(payment.workflow_state, "none")

    def test_the_money_side_freezes_but_the_booking_side_does_not(self):
        request = self._authorized_with_payments()
        payment = request.payment_ids
        payment.action_confirm_for_bank()
        for value in ({"amount": 999.0}, {"partner_bank_id": False}):
            with self.assertRaises(UserError):
                payment.write(value)
        with self.assertRaises(UserError):
            payment.date = "2026-02-02"
        # The accounting maker's own side stays open — that is what their step is for.
        payment.ref = "corrected by accounting"
        payment.move_id.line_ids[:1].analytic_distribution = self.distribution
        self.assertEqual(payment.ref, "corrected by accounting")

    def test_unconfirming_is_possible_only_before_the_file(self):
        request = self._authorized_with_payments()
        payment = request.payment_ids
        payment.action_confirm_for_bank()
        payment.action_unconfirm()
        self.assertEqual(payment.finance_state, "draft")
        # Once it is in a file the bank has been told what to do.
        payment.action_confirm_for_bank()
        payment.export_status = "exported"
        with self.assertRaises(UserError):
            payment.action_unconfirm()

    def test_confirming_paid_hands_the_request_to_the_accounting_office(self):
        request = self._authorized_with_payments(self.cash_account)
        payment = request.payment_ids
        request.action_confirm_paid()
        self.assertEqual(request.state, "paid")
        # One press stands for every payee: the vouchers are paid, numbered, and
        # waiting in draft for the accounting maker — not in the approval queue.
        self.assertEqual(payment.finance_state, "paid")
        self.assertTrue(payment.name and payment.name != "/")
        self.assertEqual(payment.state, "draft")
        self.assertEqual(payment.workflow_state, "none")
        # And the accounting office was told, on the request they navigate by.
        self.assertTrue(
            request.activity_ids.filtered(
                lambda activity: activity.activity_type_id
                == self.env.ref("disbursement_finance_kmitl.mail_activity_dr_to_book")
            )
        )

    def test_a_voucher_on_a_request_is_not_confirmed_one_by_one(self):
        request = self._authorized_with_payments(self.cash_account)
        request.payment_ids.action_confirm_for_bank()
        with self.assertRaises(UserError):
            request.payment_ids.action_confirm_paid()

    def test_confirming_paid_refuses_a_transfer_that_never_left_in_a_file(self):
        request = self._authorized_with_payments()
        payment = request.payment_ids
        self.assertTrue(payment.needs_bank_export)
        payment.action_confirm_for_bank()
        with self.assertRaises(UserError):
            request.action_confirm_paid()
        # The file was built and sent: the confirmation is the officer's to give.
        payment.export_status = "exported"
        request.action_confirm_paid()
        self.assertEqual(payment.finance_state, "paid")

    def test_the_accounting_office_books_a_paid_request_in_one_press(self):
        request = self._authorized_with_payments(self.cash_account)
        request.action_confirm_paid()
        request.action_submit_payments()
        payment = request.payment_ids
        # Their maker step is done and the approver has been asked.
        self.assertEqual(payment.state, "submitted")
        self.assertEqual(payment.workflow_state, "to_approve")
        # And the request has nothing left for them to book.
        with self.assertRaises(UserError):
            request.action_submit_payments()

    def test_posting_waits_for_the_finance_office(self):
        request = self._authorized_with_payments(self.cash_account)
        payment = request.payment_ids
        payment.action_confirm_for_bank()
        with self.assertRaises(UserError):
            payment.move_id._post()

    def test_a_rebuild_keeps_the_withholding_tax_identity(self):
        """Core rebuilds a payment's entry from the *amount* of its write-off lines
        only, merging them into one anonymous line. The values it is handed have to
        carry the withholding tax too, or the certificate and the ภ.ง.ด. report lose
        what they are made of — and the accounting maker rebuilds the entry every
        time they correct the operation type."""
        request = self._authorized_with_payments()
        payment = request.payment_ids
        wht = self.env["account.withholding.tax"].search([], limit=1)
        self.assertTrue(wht, "the KMITL chart seeds the withholding taxes")
        vals = payment._write_off_line_vals(payment.move_id.line_ids[:1])
        self.assertIn("wht_tax_id", vals)
        self.assertIn("tax_base_amount", vals)
        stashed = [dict(vals, wht_tax_id=wht.id, tax_base_amount=1000.0)]
        prepared = payment.with_context(
            kmitl_preserved_write_off={payment.id: stashed}
        )._prepare_move_line_default_vals()
        self.assertEqual(prepared[-1]["wht_tax_id"], wht.id)
        self.assertEqual(prepared[-1]["tax_base_amount"], 1000.0)

    def test_cash_payment_skips_the_bank_export_gate(self):
        request = self._billed_request([self.payee_ktb], self.subject_vendor)
        request.payment_line_ids.write(
            {
                "paying_account_id": self.cash_account.id,
                "paying_account_match": "manual",
            }
        )
        request.action_audit()
        request.action_authorize()
        request.action_create_payment()
        payment = request.payment_ids
        self.assertFalse(payment.needs_bank_export)


@tagged("post_install", "-at_install")
class TestPaymentSubject(TransactionCase):
    """The subject's own derivation, away from a disbursement."""

    def test_fallback_is_used_when_no_allowed_account_matches(self):
        subject = self.env.ref("finance_kmitl.payment_subject_advance_reimburse")
        other_bank = self.env["res.bank"].create(
            {"name": "Nowhere Bank", "bic": "NWHRTHBK"}
        )
        account, match = subject._paying_account_with_match(other_bank)
        self.assertEqual(account, subject.default_paying_account_id)
        self.assertEqual(match, "fallback")

    def test_a_fixed_subject_reports_its_account_as_main(self):
        subject = self.env.ref("finance_kmitl.payment_subject_vendor_direct")
        account, match = subject._paying_account_with_match(self.env["res.bank"])
        self.assertEqual(account, subject.default_paying_account_id)
        self.assertEqual(match, "main")
