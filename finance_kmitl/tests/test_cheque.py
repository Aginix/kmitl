# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestCheque(TransactionCase):
    """The cheque: what it reads off its voucher, how it is numbered, and what
    each of its states claims.

    Two of KMITL's three cheque หัวจ่าย are used throughout, because most of what
    went wrong before was one cheque book being mistaken for another: they are
    both SCB, both drawn under ใบสำคัญจ่าย (PV), and differ only in the bank
    account behind them — which is exactly the difference the old register could
    not see.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Cheque = cls.env["cheque.register"]
        cls.Payment = cls.env["account.payment"]

        cls.book_one = cls.env.ref("account_kmitl.paying_account_1112220015_cheque")
        cls.book_two = cls.env.ref("account_kmitl.paying_account_1112120025_cheque")
        cls.transfer_account = cls.env.ref(
            "account_kmitl.paying_account_1112120002_transfer"
        )
        cls.cash_account = cls.env.ref("account_kmitl.paying_account_1111000002_cash")
        cls.payment_type = cls.env.ref("finance_kmitl.payment_type_normal_outbound")
        cls.payable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", cls.env.company.id),
            ],
            limit=1,
        )
        cls.payee = cls.env["res.partner"].create(
            {
                "name": "การไฟฟ้านครหลวง",
                "property_account_payable_id": cls.payable_account.id,
            }
        )

    # ------------------------------------------------------------------
    def _make_payment(self, paying_account=None, amount=1000.0):
        """A voucher confirmed for the bank — the only kind a cheque may be
        written for."""
        paying_account = paying_account or self.book_one
        payment = self.Payment.create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
                "amount": amount,
                "date": "2026-01-15",
                "journal_id": paying_account.journal_id.id,
                "payment_method_line_id": paying_account.id,
                "kmitl_payment_type_id": self.payment_type.id,
            }
        )
        payment.action_confirm_for_bank()
        return payment

    def _write_cheque(self, payment, number="0512001"):
        payment.action_create_cheques()
        cheque = payment.cheque_id
        cheque.cheque_number = number
        return cheque

    def _issued(self, payment=None, number="0512001"):
        cheque = self._write_cheque(payment or self._make_payment(), number)
        cheque.action_issue()
        return cheque

    # ------------------------------------------------------------------
    # What a cheque reads off its voucher
    # ------------------------------------------------------------------
    def test_a_cheque_states_nothing_the_voucher_already_states(self):
        """One cheque pays one voucher, so there is no second copy of the payee,
        the amount or the account to drift from the first."""
        payment = self._make_payment(amount=1234.0)

        cheque = self._write_cheque(payment)

        self.assertEqual(cheque.partner_id, self.payee)
        self.assertEqual(cheque.amount, 1234.0)
        self.assertEqual(cheque.currency_id, payment.currency_id)
        self.assertEqual(cheque.paying_account_id, self.book_one)
        self.assertEqual(cheque.payment_id.cheque_id, cheque)

    def test_the_cheque_book_is_the_bank_account_not_the_journal(self):
        """The bug this replaces: the register took ``journal_id`` from the
        payment, which is always ใบสำคัญจ่าย (PV) and holds no bank at all — so
        every cheque reported the same book and no bank."""
        cheque = self._write_cheque(self._make_payment())

        self.assertEqual(cheque.cheque_book_id, self.book_one.bank_account_id)
        self.assertTrue(cheque.bank_id)
        self.assertEqual(cheque.bank_id, self.book_one.bank_account_id.bank_id)
        self.assertNotEqual(cheque.cheque_book_id, self.book_one.journal_id)

    # ------------------------------------------------------------------
    # Numbering: a guess, held nowhere
    # ------------------------------------------------------------------
    def test_a_run_of_cheques_is_written_in_one_press_and_numbered_in_order(self):
        """Twenty vouchers off one book is one press and one pass down a column,
        not twenty forms — the thing ADR-0006 took out of this phase."""
        payments = self.Payment.browse()
        for _index in range(3):
            payments |= self._make_payment()
        first = self._write_cheque(payments[0], "0512007")
        first.action_issue()

        payments[1:].action_create_cheques()

        written = self.Cheque.search(
            [("payment_id", "in", payments[1:].ids)], order="id"
        )
        self.assertEqual(
            written.mapped("cheque_number"),
            ["0512008", "0512009"],
            "the guess should run on from the last one spent in the book",
        )

    def test_the_guess_keeps_the_padding_the_book_prints_in(self):
        """``"0512009" + 1`` is ``"0512010"``, not ``512010``: the width comes
        from the paper already seen."""
        self._issued(number="0512009")

        self.assertEqual(
            self.Cheque._next_number_for_book(self.book_one.bank_account_id),
            "0512010",
        )

    def test_numbers_are_compared_as_numbers_not_as_text(self):
        """``"0512010" < "0512009"`` is true of strings and false of cheques, so
        sorting the text would propose a number already spent."""
        self._issued(number="0512009")
        self._issued(payment=self._make_payment(), number="0512010")

        self.assertEqual(
            self.Cheque._next_number_for_book(self.book_one.bank_account_id),
            "0512011",
        )

    def test_each_cheque_book_is_guessed_separately(self):
        """Numbers run without repeating within one book and mean nothing across
        books. The old constraint keyed on the journal, which is the same for
        every KMITL cheque, so all three books shared one number space."""
        self._issued(number="0512007")

        second_book = self._make_payment(self.book_two)
        second_book.action_create_cheques()

        self.assertFalse(
            self.Cheque.search([("payment_id", "=", second_book.id)]).cheque_number,
            "a book nothing has been drawn on yet has nothing to guess from",
        )

    @mute_logger("odoo.sql_db")
    def test_a_spent_number_is_never_handed_to_a_second_payee(self):
        self._issued(number="0512007")

        with self.assertRaises(IntegrityError):
            self._write_cheque(self._make_payment(), "0512007")
            self.env.flush_all()

    def test_a_cancelled_cheque_still_holds_its_number(self):
        """Its paper is gone; the number it was torn off with is spent."""
        cheque = self._issued(number="0512007")

        cheque._cancel("misprinted")

        self.assertEqual(cheque.cheque_number, "0512007")
        self.assertEqual(
            self.Cheque._next_number_for_book(self.book_one.bank_account_id),
            "0512008",
            "the next guess is past the dead one, not back onto it",
        )

    def test_a_cheque_started_by_hand_is_offered_the_guess_too(self):
        """The batch button numbered its run and the form offered nothing, so a
        cheque made from the cheque screen was retyped for no reason."""
        self._issued(number="0512007")
        later = self._make_payment()

        fresh = self.Cheque.new({"payment_id": later.id})
        fresh._onchange_payment_id()

        self.assertEqual(fresh.cheque_number, "0512008")

    def test_the_guess_does_not_overwrite_a_number_already_typed(self):
        self._issued(number="0512007")
        later = self._make_payment()

        fresh = self.Cheque.new(
            {"payment_id": later.id, "cheque_number": "0600001"}
        )
        fresh._onchange_payment_id()

        self.assertEqual(fresh.cheque_number, "0600001")

    # ------------------------------------------------------------------
    # Numbering a whole run at once
    # ------------------------------------------------------------------
    def _drafts(self, count=3, paying_account=None):
        payments = self.Payment.browse()
        for _index in range(count):
            payments |= self._make_payment(paying_account)
        payments.action_create_cheques()
        return self.Cheque.search([("payment_id", "in", payments.ids)], order="id")

    def test_a_fresh_book_leaves_the_whole_run_blank(self):
        """Nothing to guess from, which is exactly the case the run-numbering
        wizard exists for. Asserted so the wizard's reason for being does not
        quietly disappear."""
        cheques = self._drafts()

        self.assertEqual(cheques.mapped("cheque_number"), [False, False, False])

    def test_numbering_a_run_counts_on_from_the_first(self):
        cheques = self._drafts()
        wizard = self.env["cheque.register.assign.numbers"].create(
            {"cheque_ids": [(6, 0, cheques.ids)], "first_number": "0512007"}
        )

        wizard.action_assign()

        self.assertEqual(
            cheques.sorted("id").mapped("cheque_number"),
            ["0512007", "0512008", "0512009"],
        )

    def test_the_wizard_starts_from_the_guess_when_there_is_one(self):
        self._issued(number="0512007")
        cheques = self._drafts(count=2)

        wizard = self.env["cheque.register.assign.numbers"].create(
            {"cheque_ids": [(6, 0, cheques.ids)]}
        )

        self.assertEqual(wizard.first_number, "0512008")
        self.assertEqual(wizard.last_number, "0512009")

    def test_a_run_may_not_land_on_a_number_already_spent(self):
        """Caught before anything is written, and named, rather than left to the
        database to refuse one row in from the start."""
        self._issued(number="0512008")
        cheques = self._drafts(count=3)
        wizard = self.env["cheque.register.assign.numbers"].create(
            {"cheque_ids": [(6, 0, cheques.ids)], "first_number": "0512007"}
        )

        with self.assertRaises(UserError) as caught:
            wizard.action_assign()

        self.assertIn("0512008", str(caught.exception))
        self.assertFalse(any(cheques.mapped("cheque_number")))

    def test_an_issued_cheque_is_not_renumbered(self):
        issued = self._issued(number="0512007")

        with self.assertRaises(UserError):
            issued.action_open_assign_numbers()

    def test_a_run_is_numbered_one_book_at_a_time(self):
        first = self._drafts(count=1)
        second = self._drafts(count=1, paying_account=self.book_two)

        with self.assertRaises(UserError):
            (first | second).action_open_assign_numbers()

    # ------------------------------------------------------------------
    # What may be written for, and how many
    # ------------------------------------------------------------------
    def test_a_voucher_has_at_most_one_live_cheque(self):
        payment = self._make_payment()
        self._write_cheque(payment, "0512007")

        with self.assertRaises(UserError):
            payment.action_create_cheques()

    def test_a_voucher_may_have_several_dead_ones(self):
        """A voucher accumulates as many rows as it took pieces of paper."""
        payment = self._make_payment()
        first = self._write_cheque(payment, "0512007")

        replacement = first._cancel("misprinted", replace=True)

        self.assertEqual(len(payment.cheque_ids), 2)
        self.assertEqual(payment.cheque_id, replacement)
        self.assertEqual(replacement.cheque_number, "0512008")

    def test_a_transfer_gets_no_cheque(self):
        with self.assertRaises(UserError):
            self._make_payment(self.transfer_account).action_create_cheques()

    def test_an_unconfirmed_voucher_gets_no_cheque(self):
        """What the cheque would be written for could still change underneath
        it — the same gate an e-payment file puts on its rows."""
        payment = self._make_payment()
        payment.action_unconfirm()

        with self.assertRaises(UserError):
            payment.action_create_cheques()

    def test_the_selection_is_refused_by_name(self):
        """Ticking twenty and getting eighteen would leave the officer to work
        out which two are missing."""
        good, bad = self._make_payment(), self._make_payment(self.transfer_account)

        with self.assertRaises(UserError) as caught:
            (good | bad).action_create_cheques()

        self.assertIn(bad.display_name, str(caught.exception))

    # ------------------------------------------------------------------
    # The paper freezes when it is made
    # ------------------------------------------------------------------
    def test_a_cheque_cannot_be_issued_without_a_number(self):
        """A draft may sit without one — the officer has the voucher before they
        have the paper in their hand."""
        payment = self._make_payment()
        payment.action_create_cheques()
        cheque = payment.cheque_id
        self.assertFalse(cheque.cheque_number)

        with self.assertRaises(UserError):
            cheque.action_issue()

    def test_the_number_and_the_date_freeze_when_the_cheque_is_issued(self):
        """They are printed on paper this system no longer controls."""
        cheque = self._issued(number="0512007")

        with self.assertRaises(UserError):
            cheque.cheque_number = "0512008"
        with self.assertRaises(UserError):
            cheque.cheque_date = "2026-02-01"
        # The note is not the paper's, and stays writable.
        cheque.note = "collected by the meter reader"

    def test_a_draft_cheque_is_not_printed(self):
        payment = self._make_payment()
        payment.action_create_cheques()

        with self.assertRaises(UserError):
            payment.cheque_id.action_print_cheque()

    # ------------------------------------------------------------------
    # Handing it over is the Hand-over
    # ------------------------------------------------------------------
    def test_issuing_does_not_pay_anyone(self):
        """A cheque printed and signed can wait days in a drawer. ADR-0004's
        distinction, on the cheque side."""
        cheque = self._issued()

        self.assertEqual(cheque.state, "issued")
        self.assertEqual(cheque.payment_id.finance_state, "confirmed")

    def test_handing_it_over_pays_the_voucher(self):
        cheque = self._issued()

        cheque.action_hand_over()

        self.assertEqual(cheque.state, "paid")
        self.assertEqual(cheque.payment_id.finance_state, "paid")
        self.assertTrue(cheque.handover_date)

    def test_a_cheque_is_not_confirmed_on_its_voucher(self):
        """A transfer is confirmed by closing its file, a cheque by handing the
        cheque over. What that press is left for is cash."""
        cheque = self._issued()

        with self.assertRaises(UserError):
            cheque.payment_id.action_confirm_paid()

    def test_cash_is_still_confirmed_on_its_voucher(self):
        """Nothing else in the system records money crossing a counter."""
        payment = self._make_payment(self.cash_account)

        payment.action_confirm_paid()

        self.assertEqual(payment.finance_state, "paid")

    # ------------------------------------------------------------------
    # A dead cheque takes its voucher back (ADR-0006)
    # ------------------------------------------------------------------
    def test_a_cheque_that_dies_before_it_is_collected_leaves_the_voucher_alone(self):
        """Nothing was asserted yet: the voucher is still confirmed."""
        cheque = self._issued(number="0512007")

        replacement = cheque._cancel("misprinted", replace=True)

        self.assertEqual(cheque.state, "cancelled")
        self.assertEqual(cheque.payment_id.finance_state, "confirmed")
        self.assertEqual(replacement.state, "draft")

    def test_a_cheque_that_dies_after_it_is_collected_withdraws_the_claim(self):
        """มอบเช็ค asserted the money reached the payee, and it did not."""
        cheque = self._issued(number="0512007")
        cheque.action_hand_over()
        self.assertEqual(cheque.payment_id.finance_state, "paid")

        replacement = cheque._cancel("bounced", replace=True)

        self.assertEqual(cheque.cancel_reason, "bounced")
        self.assertEqual(
            cheque.payment_id.finance_state,
            "confirmed",
            "the voucher is the finance office's again, and no longer postable",
        )
        self.assertEqual(replacement.payment_id, cheque.payment_id)

    def test_the_replacement_is_written_on_the_same_voucher(self):
        """Only the instrument died. A new ใบสำคัญจ่าย number would read as a
        second thing owed."""
        cheque = self._issued(number="0512007")
        voucher_number = cheque.payment_id.name

        replacement = cheque._cancel("lost", replace=True)

        self.assertEqual(replacement.payment_id.name, voucher_number)
        self.assertEqual(replacement.cheque_number, "0512008")

    def test_a_cheque_may_die_without_a_successor(self):
        """The whole disbursement is being unwound, not re-paid."""
        cheque = self._issued(number="0512007")

        replacement = cheque._cancel("misdrawn")

        self.assertFalse(replacement)
        self.assertFalse(cheque.payment_id.cheque_id)

    def test_a_posted_entry_is_the_accounting_office_s_to_reverse(self):
        """Once they have posted, the bank credit is in the books, and taking it
        out is a reversal on their form."""
        cheque = self._issued(number="0512007")
        cheque.action_hand_over()
        cheque.payment_id.move_id.state = "posted"

        with self.assertRaises(UserError):
            cheque._cancel("bounced")

    def test_a_cheque_cannot_die_twice(self):
        cheque = self._issued(number="0512007")
        cheque._cancel("lost")

        with self.assertRaises(UserError):
            cheque._cancel("bounced")

    # ------------------------------------------------------------------
    # What the statusbar says
    # ------------------------------------------------------------------
    def test_the_cheque_statusbar_splits_what_the_voucher_holds_as_one(self):
        """A cheque voucher is `confirmed` both before the paper is written and
        while it sits signed in a drawer. The voucher is right to hold those as
        one state; a bar an officer works from is not."""
        payment = self._make_payment()
        self.assertEqual(payment.finance_state_cheque, "confirmed")

        cheque = self._write_cheque(payment)
        self.assertEqual(
            payment.finance_state_cheque,
            "confirmed",
            "a cheque made but not yet written on is still 'to be written'",
        )

        cheque.action_issue()
        self.assertEqual(payment.finance_state, "confirmed")
        self.assertEqual(payment.finance_state_cheque, "issued")

        cheque.action_hand_over()
        self.assertEqual(payment.finance_state_cheque, "paid")

    # ------------------------------------------------------------------
    # Withholding tax
    # ------------------------------------------------------------------
    def test_the_withholding_certificate_is_dated_from_the_cheque(self):
        """The law dates the withholding by the day the income was paid, and for
        a cheque that is the day written on it — the day the payee may present
        it. Not the voucher's date, which is the day it was authorised, and not
        the day it was collected, which has no tax effect at all.
        """
        payment = self._make_payment()
        Cert = self.env["withholding.tax.cert"]
        # Before the cheque exists, the voucher's own date is all there is.
        self.assertEqual(Cert.new({"payment_id": payment.id}).date, payment.date)

        cheque = self._write_cheque(payment)
        cheque.cheque_date = "2026-10-03"
        cheque.action_issue()

        self.assertEqual(
            Cert.new({"payment_id": payment.id}).date,
            fields.Date.to_date("2026-10-03"),
        )

        # Collected six days later, in the same month or another: it makes no
        # difference to the filing.
        cheque.handover_date = "2026-10-09"
        cheque.action_hand_over()

        self.assertEqual(
            Cert.new({"payment_id": payment.id}).date,
            fields.Date.to_date("2026-10-03"),
        )
        # And the voucher has not moved with it: its number says which month it
        # is in, and a number that has been issued must not change.
        self.assertEqual(payment.date, fields.Date.to_date("2026-01-15"))

    # ------------------------------------------------------------------
    # Nothing here goes to a bank
    # ------------------------------------------------------------------
    def test_a_cheque_never_enters_an_e_payment_file(self):
        payment = self._make_payment()

        self.assertFalse(payment.needs_bank_export)
        with self.assertRaises(UserError):
            payment.action_create_bank_payment_export()

    def test_a_cheque_needs_a_book_to_be_drawn_on(self):
        """A paying account with no bank account is not a cheque book, so there is
        nothing for the cheque to be torn from or numbered against. The
        disbursement audit refuses such a payee earlier; this is the backstop for
        a voucher filled in by hand."""
        self.book_two.bank_account_id = False
        payment = self._make_payment(self.book_two)

        with self.assertRaises(ValidationError):
            self.Cheque.create({"payment_id": payment.id})
