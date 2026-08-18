# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.account_kmitl.hooks import PAYING_ACCOUNTS
from odoo.addons.finance_kmitl.hooks import PAYMENT_SUBJECTS


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

        # A subject paid from one fixed หัวจ่าย, and one that matches the payee's
        # own bank and falls back to SCB ย่อยเทคโนฯ.
        cls.subject_fixed = cls.env.ref("finance_kmitl.payment_subject_company_revenue")
        cls.subject_auto = cls.env.ref("finance_kmitl.payment_subject_person_revenue")

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
        request.payment_subject_id = subject or self.subject_fixed
        return request

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------
    def test_paying_accounts_are_seeded_with_their_bank(self):
        journal = self.env.ref("account_kmitl.journal_pv")
        paying = journal.outbound_payment_method_line_ids.filtered("payment_account_id")
        self.assertEqual(len(paying), len(PAYING_ACCOUNTS))
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
        request = self._authorized_without_payments()
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
            [self.payee_ktb, self.payee_other], self.subject_fixed
        )
        lines = request.payment_line_ids
        self.assertEqual(
            set(lines.mapped("paying_account_id").ids), {self.scb_account.id}
        )
        self.assertEqual(set(lines.mapped("paying_account_match")), {"main"})

    def test_auto_match_serves_a_payee_from_their_own_bank(self):
        request = self._billed_request(
            [self.payee_ktb, self.payee_other], self.subject_auto
        )
        by_payee = {line.partner_id: line for line in request.payment_line_ids}
        self.assertEqual(by_payee[self.payee_ktb].paying_account_id, self.ktb_account)
        self.assertEqual(by_payee[self.payee_ktb].paying_account_match, "bank")
        # Nobody banks there: falls back to the subject's account.
        self.assertEqual(by_payee[self.payee_other].paying_account_id, self.scb_account)
        self.assertEqual(by_payee[self.payee_other].paying_account_match, "fallback")

    def test_a_hand_picked_account_survives_re_derivation(self):
        request = self._billed_request([self.payee_ktb], self.subject_auto)
        line = request.payment_line_ids
        line.write(
            {
                "paying_account_id": self.cheque_account.id,
                "paying_account_match": "manual",
            }
        )
        request.payment_subject_id = self.subject_fixed
        self.assertEqual(line.paying_account_id, self.cheque_account)
        self.assertEqual(line.paying_account_match, "manual")

    def test_method_follows_the_paying_account(self):
        request = self._billed_request([self.payee_ktb], self.subject_auto)
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
        form = self._unsaved_form(request, self.subject_auto)
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
        request = self._billed_request([self.payee_ktb], self.subject_auto)
        request.payment_line_ids.write(
            {
                "paying_account_id": self.cheque_account.id,
                "paying_account_match": "manual",
            }
        )
        form = self._unsaved_form(request, self.subject_fixed)
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
        request.payment_subject_id = self.subject_fixed
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
            [self.payee_ktb, self.payee_other], self.subject_auto
        )
        request.action_audit()
        request.action_authorize()
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
        # And every voucher records why it leaves the account it leaves.
        self.assertEqual(
            set(request.payment_ids.mapped("kmitl_payment_subject_id")),
            {self.subject_auto},
        )

    def test_banking_coordinates_freeze_once_the_payment_exists(self):
        request = self._billed_request([self.payee_ktb], self.subject_fixed)
        request.action_audit()
        request.action_authorize()
        with self.assertRaises(UserError):
            request.payment_line_ids.paying_account_id = self.ktb_account

    # ------------------------------------------------------------------
    # Two lifecycles on one voucher (ADR-0005)
    # ------------------------------------------------------------------
    def _authorized_with_payments(self, paying_account=None):
        """A request whose vouchers exist and are still the finance office's.

        Authorising is what raises them (ADR-0006), so there is nothing to press
        after it: they come back numbered and confirmed for the bank.
        """
        request = self._billed_request([self.payee_ktb], self.subject_fixed)
        if paying_account:
            request.payment_line_ids.write(
                {
                    "paying_account_id": paying_account.id,
                    "paying_account_match": "manual",
                }
            )
        request.action_audit()
        request.action_authorize()
        return request

    def _authorized_without_payments(self):
        """A request the authorisation could not raise vouchers for.

        The payee's account is removed after the audit passed, which is the shape
        every real failure has: a banking coordinate that was right when the
        auditor checked it and is not right now.
        """
        request = self._billed_request([self.payee_ktb], self.subject_fixed)
        request.action_audit()
        self.payee_ktb.bank_ids.unlink()
        request.action_authorize()
        return request

    def test_authorising_raises_the_vouchers_ready_for_the_bank(self):
        request = self._authorized_with_payments()
        payment = request.payment_ids
        self.assertEqual(len(payment), 1)
        # Numbered and frozen, which is what an e-payment file needs...
        self.assertEqual(payment.finance_state, "confirmed")
        self.assertTrue(payment.name and payment.name != "/")
        # ...dated the day it was authorised, which is the month its number is
        # in and therefore the period it books in.
        self.assertTrue(payment.date)
        # ...and still the accounting office's untouched draft.
        self.assertEqual(payment.state, "draft")
        self.assertEqual(payment.workflow_state, "none")

    def test_a_failure_to_raise_the_vouchers_leaves_the_request_authorized(self):
        request = self._authorized_without_payments()
        # The authorisation stands: the coordinate is not the authorizer's to fix.
        self.assertEqual(request.state, "payment_authorized")
        self.assertFalse(request.payment_ids)
        self.assertTrue(
            any(
                "Create Payment" in (message.body or "")
                for message in request.message_ids
            ),
            "the reason belongs in the chatter, with the way back in",
        )
        # And the way back in works once the coordinate is right again.
        self.env["res.partner.bank"].create(
            {
                "partner_id": self.payee_ktb.id,
                "acc_number": "TEST-restored",
                "bank_id": self.ktb_account.bank_id.id,
            }
        )
        request.payment_line_ids.partner_bank_id = self.payee_ktb.bank_ids[:1]
        request.action_create_payment()
        self.assertEqual(request.payment_ids.finance_state, "confirmed")

    def test_the_money_side_freezes_but_the_booking_side_does_not(self):
        request = self._authorized_with_payments()
        payment = request.payment_ids
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
        """The finance office's one way to correct a voucher.

        They have no window on the payment line any more — the authorisation
        raises the voucher and freezes the money side with it — so taking the
        voucher back off the bank's desk is how a wrong coordinate is fixed, for
        as long as nothing has been sent.
        """
        request = self._authorized_with_payments()
        payment = request.payment_ids
        payment.action_unconfirm()
        self.assertEqual(payment.finance_state, "draft")
        payment.partner_bank_id = self.payee_ktb.bank_ids[:1]
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
                lambda activity: (
                    activity.activity_type_id
                    == self.env.ref(
                        "disbursement_finance_kmitl.mail_activity_dr_to_book"
                    )
                )
            )
        )

    def _book_todos(self, request):
        return request.activity_ids.filtered(
            lambda activity: (
                activity.activity_type_id
                == self.env.ref("disbursement_finance_kmitl.mail_activity_dr_to_book")
            )
        )

    def test_the_request_crosses_when_its_last_voucher_is_paid(self):
        """Nobody presses จ่ายครบ for the request. Its payees leave in as many
        e-payment files as they have หัวจ่าย, each closed by whoever handled it, and
        the request crosses when the last voucher lands (ADR-0007)."""
        request = self._billed_request([self.payee_ktb, self.payee_other])
        request.payment_subject_id = self.subject_fixed
        request.action_audit()
        request.action_authorize()
        payments = request.payment_ids
        self.assertEqual(len(payments), 2)
        self.assertEqual(request.state, "payment_authorized")

        first, second = payments[0], payments[1]
        first._mark_paid()
        self.assertEqual(
            request.state,
            "payment_authorized",
            "one payee paid is not every payee paid",
        )
        self.assertFalse(self._book_todos(request))

        second._mark_paid()

        self.assertEqual(request.state, "paid")
        # One Todo *per accounting maker*, not one in total — the group carries
        # several users, so the count is the group's size and not worth asserting.
        self.assertTrue(self._book_todos(request))

    def test_the_request_is_not_handed_over_twice(self):
        """``_hand_over`` is reached from the voucher write and from the override
        press, and the accounting office must not get the same Todo twice."""
        request = self._authorized_with_payments(self.cash_account)
        request.payment_ids._mark_paid()
        self.assertEqual(request.state, "paid")
        todos = len(self._book_todos(request))

        request._hand_over()

        self.assertEqual(len(self._book_todos(request)), todos)

    def test_a_voucher_never_confirmed_holds_the_request(self):
        """Intended: it has not been paid, so the accounting office has nothing to
        book for it. The finance office's own Todo stays open to say so."""
        request = self._authorized_with_payments(self.cash_account)
        paid = request.payment_ids
        stray = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee_ktb.id,
                "amount": 500.0,
                "date": "2026-01-15",
                "journal_id": self.cash_account.journal_id.id,
                "payment_method_line_id": self.cash_account.id,
                "kmitl_payment_type_id": paid.kmitl_payment_type_id.id,
                "disbursement_request_id": request.id,
            }
        )
        self.assertEqual(stray.finance_state, "draft")

        paid._mark_paid()

        self.assertEqual(request.state, "payment_authorized")
        self.assertIn("1/2", request.payment_status_display)

    def test_a_transfer_on_a_request_is_not_confirmed_one_by_one(self):
        """It goes out in an e-payment file, and closing that file is already the
        press. Giving it twice for one fact is how half a request gets handed over."""
        request = self._authorized_with_payments()
        self.assertTrue(request.payment_ids.needs_bank_export)
        with self.assertRaises(UserError):
            request.payment_ids.action_confirm_paid()

    def test_a_cheque_payee_on_a_request_is_confirmed_on_itself(self):
        """It enters no file, so there is nothing else to close. Before this, such a
        payee had no reachable press at all once the request's own button went to
        developer mode, and its request sat at payment_authorized forever."""
        request = self._authorized_with_payments(self.cheque_account)
        payment = request.payment_ids
        self.assertFalse(payment.needs_bank_export)

        payment.action_confirm_paid()

        self.assertEqual(payment.finance_state, "paid")
        self.assertEqual(request.state, "paid")
        # The request handed over, and the voucher did not do it a second time.
        self.assertTrue(self._book_todos(request))
        self.assertFalse(payment.move_id.activity_ids)

    def test_the_request_crosses_when_the_last_voucher_is_cancelled(self):
        """The condition is "nothing left unpaid", and a voucher can stop being
        unpaid by leaving as well as by being paid."""
        request = self._billed_request([self.payee_ktb, self.payee_other])
        request.payment_subject_id = self.subject_fixed
        request.action_audit()
        request.action_authorize()
        first, second = request.payment_ids[0], request.payment_ids[1]
        first._mark_paid()
        self.assertEqual(request.state, "payment_authorized")

        second.action_cancel()

        self.assertEqual(request.state, "paid")

    def test_confirming_paid_refuses_a_transfer_that_never_left_in_a_file(self):
        request = self._authorized_with_payments()
        payment = request.payment_ids
        self.assertTrue(payment.needs_bank_export)
        with self.assertRaises(UserError):
            request.action_confirm_paid()
        # The file was built and sent: the confirmation is the officer's to give.
        payment.export_status = "exported"
        request.action_confirm_paid()
        self.assertEqual(payment.finance_state, "paid")

    def test_payment_progress_counts_what_the_finance_office_paid(self):
        """The smart button reports money out, not entries booked.

        The two are different offices' facts about the same voucher: a request is
        paid in full at the Hand-over and stays unbooked until the accounting
        maker gets to it, so counting posted moves showed a fully paid request as
        nothing paid.
        """
        request = self._authorized_with_payments(self.cash_account)
        self.assertIn("0/1", request.payment_status_display)
        request.action_confirm_paid()
        self.assertEqual(request.payment_ids.finance_state, "paid")
        # Still nobody's entry, and still counted as paid.
        self.assertEqual(request.payment_ids.state, "draft")
        self.assertIn("1/1", request.payment_status_display)

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
        request = self._billed_request([self.payee_ktb], self.subject_fixed)
        request.payment_line_ids.write(
            {
                "paying_account_id": self.cash_account.id,
                "paying_account_match": "manual",
            }
        )
        request.action_audit()
        request.action_authorize()
        payment = request.payment_ids
        self.assertFalse(payment.needs_bank_export)

    # ------------------------------------------------------------------
    # The trail back to the request (ADR-0006)
    # ------------------------------------------------------------------
    def test_a_voucher_and_its_entry_both_lead_back_to_the_request(self):
        request = self._authorized_with_payments(self.cash_account)
        payment = request.payment_ids
        self.assertEqual(payment.disbursement_request_id, request)
        self.assertEqual(
            payment.action_view_disbursement_request()["res_id"], request.id
        )
        # The accounting office works on the entry, so the trail has to be there
        # too — read through the payment, never stored on the move, or the
        # voucher would land in the request's bill list.
        move = payment.move_id
        self.assertEqual(move.payment_disbursement_request_id, request)
        self.assertEqual(
            move.action_view_payment_disbursement_request()["res_id"], request.id
        )
        self.assertNotIn(move, request.bill_ids)
        # What the two buttons actually display: a Char, because a field that can
        # be edited is drawn as an input and a button is no place for one.
        self.assertEqual(payment.disbursement_request_name, request.name)
        self.assertEqual(move.payment_disbursement_request_name, request.name)

    # ------------------------------------------------------------------
    # Withholding tax is dated from the e-payment file (ADR-0006)
    # ------------------------------------------------------------------
    def test_the_wht_certificate_is_dated_the_day_the_money_left(self):
        """The voucher is dated when it was authorised, because that numbers it.

        The withholding is dated by law from the day the income was paid, and the
        only record of that day is the file's effective date — so the certificate
        reads it from there, and falls back to the voucher for a payment that
        never travels in a file.
        """
        request = self._authorized_with_payments()
        payment = request.payment_ids
        voucher_date = payment.date
        Cert = self.env["withholding.tax.cert"]
        # No file: the voucher's own date is all there is to go on.
        self.assertEqual(Cert.new({"payment_id": payment.id}).date, voucher_date)

        payment.payment_export_id = self.env["bank.payment.export"].create(
            {"effective_date": "2026-10-03"}
        )
        self.assertEqual(
            Cert.new({"payment_id": payment.id}).date,
            fields.Date.to_date("2026-10-03"),
        )
        # And the voucher itself does not move with it: its number says which
        # month it is in, and a number that has been issued must not change.
        self.assertEqual(payment.date, voucher_date)


@tagged("post_install", "-at_install")
class TestPaymentSubject(TransactionCase):
    """The subject's own derivation, away from a disbursement."""

    def test_every_payment_subject_is_seeded_and_bound(self):
        """The เรื่องที่จ่าย are made by finance_kmitl's post-init hook, which looks
        its หัวจ่าย up by (chart code, วิธีจ่าย) instead of by external id — a data
        file that ref'd those ids failed to install on any database whose chart was
        set up before account_kmitl published them. What has to hold either way is
        that each subject exists under the external id the rest of the system names
        it by, and that it actually points at a paying account."""
        for entry in PAYMENT_SUBJECTS:
            xml_id = "finance_kmitl.%s" % entry["xmlid"]
            subject = self.env.ref(xml_id, raise_if_not_found=False)
            self.assertTrue(subject, "%s was not seeded" % xml_id)
            self.assertTrue(
                subject.default_paying_account_id,
                "%s has no main/fallback paying account" % xml_id,
            )
            self.assertEqual(
                subject.default_paying_account_id.payment_method_id,
                subject.default_payment_method_id,
                "%s falls back to an account paid another way" % xml_id,
            )

    def test_fallback_is_used_when_no_allowed_account_matches(self):
        subject = self.env.ref("finance_kmitl.payment_subject_person_revenue")
        other_bank = self.env["res.bank"].create(
            {"name": "Nowhere Bank", "bic": "NWHRTHBK"}
        )
        account, match = subject._paying_account_with_match(other_bank)
        self.assertEqual(account, subject.default_paying_account_id)
        self.assertEqual(match, "fallback")

    def test_a_fixed_subject_reports_its_account_as_main(self):
        subject = self.env.ref("finance_kmitl.payment_subject_company_revenue")
        account, match = subject._paying_account_with_match(self.env["res.bank"])
        self.assertEqual(account, subject.default_paying_account_id)
        self.assertEqual(match, "main")
