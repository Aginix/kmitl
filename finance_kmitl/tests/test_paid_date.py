# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaidDate(TransactionCase):
    """วันที่จ่ายจริง: which record answers for which way of paying, and what
    the field can be filtered by.

    Every date here is relative to today, because the base module refuses an
    effective date in the past — a file is an instruction to a bank, and a bank
    cannot be told to have moved money yesterday.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Payment = cls.env["account.payment"]
        cls.Export = cls.env["bank.payment.export"]

        cls.transfer_account = cls.env.ref(
            "account_kmitl.paying_account_1112120002_transfer"
        )
        cls.cheque_account = cls.env.ref(
            "account_kmitl.paying_account_1112220015_cheque"
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
                "name": "Payee",
                "property_account_payable_id": cls.payable_account.id,
            }
        )
        cls.env["res.partner.bank"].create(
            {
                "partner_id": cls.payee.id,
                "acc_number": "1234567890",
                "bank_id": cls.transfer_account.bank_id.id,
            }
        )

        cls.today = fields.Date.context_today(cls.env.user)
        # The voucher is raised well before any of the instruments act, which is
        # the whole situation the field exists for.
        cls.voucher_date = cls.today - timedelta(days=10)

    # ------------------------------------------------------------------
    def _make_payment(self, paying_account, date=None):
        payment = self.Payment.create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.payee.id,
                "partner_bank_id": self.payee.bank_ids[:1].id,
                "amount": 1000.0,
                "date": date or self.voucher_date,
                "journal_id": paying_account.journal_id.id,
                "payment_method_line_id": paying_account.id,
                "kmitl_payment_type_id": self.payment_type.id,
            }
        )
        payment.action_confirm_for_bank()
        return payment

    def _put_in_file(self, payment, effective_date):
        export = self.Export.create(
            {
                "paying_account_id": payment.payment_method_line_id.id,
                "effective_date": effective_date,
                "export_line_ids": [(0, 0, {"payment_id": payment.id})],
            }
        )
        export.action_confirm()
        export.action_done()
        return export

    def _write_cheque(self, payment, cheque_date, number="0512001"):
        payment.action_create_cheques()
        cheque = payment.cheque_id
        cheque.write({"cheque_number": number, "cheque_date": cheque_date})
        return cheque

    # ------------------------------------------------------------------
    def test_transfer_reads_the_files_effective_date(self):
        """A voucher raised before its file takes effect is paid on the file's
        day, not on its own."""
        effective = self.today + timedelta(days=3)
        payment = self._make_payment(self.transfer_account)
        self._put_in_file(payment, effective)

        self.assertEqual(payment.paid_date, effective)
        self.assertNotEqual(payment.paid_date, payment.date)

    def test_transfer_without_an_effective_date_falls_to_the_voucher(self):
        """BAY and KBANK files do not require one — the voucher date is then the
        only answer anything in the system has."""
        payment = self._make_payment(self.transfer_account)
        self._put_in_file(payment, False)

        self.assertEqual(payment.paid_date, payment.date)

    def test_cheque_reads_the_date_on_the_paper(self):
        cheque_date = self.today + timedelta(days=2)
        payment = self._make_payment(self.cheque_account)
        self._write_cheque(payment, cheque_date)

        self.assertEqual(payment.paid_date, cheque_date)

    def test_a_cancelled_cheque_answers_for_nothing(self):
        """Its date is not the day anybody was paid, so the voucher falls back
        to its own — and by ADR-0007 the voucher is back at confirmed anyway."""
        payment = self._make_payment(self.cheque_account)
        cheque = self._write_cheque(payment, self.today + timedelta(days=2))
        cheque._cancel("misprinted")

        self.assertFalse(payment.cheque_id)
        self.assertEqual(payment.paid_date, payment.date)

    def test_cash_is_paid_on_the_voucher_date(self):
        payment = self._make_payment(self.cash_account)

        self.assertEqual(payment.paid_date, payment.date)

    def test_the_certificate_is_dated_the_same_day(self):
        """The withholding-tax certificate now reads the field rather than
        repeating the chain, so the two can never disagree."""
        effective = self.today + timedelta(days=4)
        payment = self._make_payment(self.transfer_account)
        self._put_in_file(payment, effective)
        cert = self.env["withholding.tax.cert"].create(
            {"payment_id": payment.id, "partner_id": self.payee.id}
        )

        self.assertEqual(cert.date, payment.paid_date)

    # ------------------------------------------------------------------
    def test_search_finds_each_kind_by_its_own_date(self):
        """A range over วันที่จ่ายจริง has to reach all three branches at once."""
        effective = self.today + timedelta(days=3)
        cheque_date = self.today + timedelta(days=5)

        transfer = self._make_payment(self.transfer_account)
        self._put_in_file(transfer, effective)
        cheque_payment = self._make_payment(self.cheque_account)
        self._write_cheque(cheque_payment, cheque_date)
        cash = self._make_payment(self.cash_account)

        found = self.Payment.search(
            [
                ("id", "in", (transfer + cheque_payment + cash).ids),
                ("paid_date", ">=", self.today),
                ("paid_date", "<=", self.today + timedelta(days=10)),
            ]
        )
        self.assertEqual(found, transfer + cheque_payment)

        found = self.Payment.search(
            [
                ("id", "in", (transfer + cheque_payment + cash).ids),
                ("paid_date", "<", self.today),
            ]
        )
        self.assertEqual(found, cash)

    def test_search_narrows_to_one_day(self):
        effective = self.today + timedelta(days=3)
        cheque_date = self.today + timedelta(days=5)

        transfer = self._make_payment(self.transfer_account)
        self._put_in_file(transfer, effective)
        cheque_payment = self._make_payment(self.cheque_account)
        self._write_cheque(cheque_payment, cheque_date)

        found = self.Payment.search(
            [
                ("id", "in", (transfer + cheque_payment).ids),
                ("paid_date", "=", effective),
            ]
        )
        self.assertEqual(found, transfer)

    def test_search_does_not_let_a_dated_file_answer_a_cheques_question(self):
        """A voucher in a file *with* an effective date never reaches the cheque
        branch, so a cheque dated the same day cannot drag it in."""
        effective = self.today + timedelta(days=3)
        transfer = self._make_payment(self.transfer_account)
        self._put_in_file(transfer, effective)

        found = self.Payment.search(
            [
                ("id", "in", transfer.ids),
                ("paid_date", "=", transfer.date),
            ]
        )
        self.assertFalse(found)
