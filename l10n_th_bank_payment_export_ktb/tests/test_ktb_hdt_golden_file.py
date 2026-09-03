# Copyright 2026 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The KTB Direct Credit (H/D/T) layout, against a whole file KMITL sent KTB.

``tests/fixtures/ktb_hdt_sample.txt`` is that file: header, six details and a
trailer, nothing trimmed. Only the account numbers were replaced, keeping their
length and leading digits. The amounts, the date, the counts and the totals are
the bank's own -- and because the file is whole, the trailer's transaction count
and grand total are the ones its own six details add up to, which is what pins
the amount field's width.

That width is 10, not the 13 we used to write. Both are consistent with a single
detail record, since the field is zero-padded and the three characters after it
are always ``029``; only a file whose trailer can be reconciled against its own
body tells them apart. 10 is the one whose six amounts sum to the trailer's
``0000797826000``.

``029`` is a fixed three-character code. Every KTB file KMITL has shown us
carries it and nothing available says what it stands for -- it is treated the
same way as BAY's ``712`` and ``A001``: a constant taken from the real file,
right for this institute's setup, to be revisited if KTB ever explains it.

The other KTB product, ``ktb_ipay``, has no sample and is not covered here.
"""

from odoo import fields
from odoo.exceptions import UserError

from odoo.addons.l10n_th_bank_payment_export_format.tests.common import (
    BLANK,
    DIGITS,
    TEXT,
    CommonBankExportFormat,
)
from odoo.tests.common import tagged

HEADER = (
    ("Record Type", 1, "H"),
    ("Running Number", 6, "000001"),
    ("Sending Bank Code", 3, "006"),
    ("Sending A/C", 10, DIGITS),
    ("Company Name", 25, TEXT),
    ("Effective Date", 6, DIGITS),
    ("Reserved", 1, BLANK),
    ("Filler", 76, DIGITS),
)

DETAIL = (
    ("Record Type", 1, "D"),
    ("Running Number", 6, DIGITS),
    ("Receiving Bank Code", 3, DIGITS),
    ("Receiving A/C", 10, DIGITS),
    ("Transaction Code", 1, "C"),
    ("Amount", 10, DIGITS),
    ("Transaction Code 2", 3, "029"),
    ("Filler", 94, DIGITS),
)

TRAILER = (
    ("Record Type", 1, "T"),
    ("Total Record Count", 6, DIGITS),
    ("Sending Bank Code", 3, "006"),
    ("Sending A/C", 10, DIGITS),
    ("Reserved", 21, DIGITS),
    ("Transaction Count", 6, DIGITS),
    ("Total Amount", 13, DIGITS),
    ("Filler", 68, DIGITS),
)

# The file's date is in the past and the export refuses one; everything else in
# it, including the trailer's counts and totals, is reproducible.
HEADER_VARIABLE = ("Effective Date",)

SENDING_ACCOUNT = "0280000001"
SENDER_NAME = "KING MONGKUT LADGRABANG"
PAYEES = (
    ("0240000001", 1425602.50),
    ("6930000001", 1214455.00),
    ("6930000002", 1313908.75),
    ("6930000003", 1298368.75),
    ("6930000004", 1429765.00),
    ("0820000001", 1296160.00),
)


@tagged("post_install", "-at_install")
class TestKtbHdtGoldenFile(CommonBankExportFormat):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format = cls.env.ref("l10n_th_bank_payment_export_ktb.ktb_hdt")
        cls.bank_ktb = cls._thai_bank("KRTHTHBK", "006", "Krung Thai Bank")
        cls.journal_ktb = cls._paying_journal(cls.bank_ktb, SENDING_ACCOUNT, "TKTB")
        cls.payments = cls.env["account.payment"]
        for idx, (acc_number, amount) in enumerate(PAYEES):
            payee = cls._payee("สมชาย  ทดสอบระบบ %s" % idx, cls.bank_ktb, acc_number)
            cls.payments |= cls._posted_payment(cls.journal_ktb, payee, amount)
        cls.sample = cls._load_fixture(
            "l10n_th_bank_payment_export_ktb", "ktb_hdt_sample.txt"
        )

    def _create_ktb_export(self):
        return self._export_with_lines(
            {
                "bank": "KRTHTHBK",
                "bank_export_format_id": self.bank_export_format.id,
                "ktb_sender_name": SENDER_NAME,
                "ktb_bank_type": "direct",
                "ktb_service_type_direct": "14",
                "effective_date": fields.Date.today(),
            },
            self.payments,
        )

    def test_the_sample_still_matches_the_layout(self):
        """Guards the evidence: a re-trimmed fixture proves nothing."""
        self.assertEqual(len(self.sample), 8)
        self.assertRecordShape(self.sample[0], HEADER, "sample header")
        for idx, record in enumerate(self.sample[1:-1]):
            self.assertRecordShape(record, DETAIL, "sample detail %s" % (idx + 1))
        self.assertRecordShape(self.sample[-1], TRAILER, "sample trailer")

    def test_the_trailer_adds_up_to_the_details(self):
        """The property that decides the amount field is 10 wide, not 13."""
        details = self.sample[1:-1]
        total = sum(int(self._slice(rec, DETAIL, "Amount")) for rec in details)
        self.assertEqual(
            self._slice(self.sample[-1], TRAILER, "Total Amount"),
            str(total).rjust(13, "0"),
        )
        self.assertEqual(
            self._slice(self.sample[-1], TRAILER, "Transaction Count"),
            str(len(details)).rjust(6, "0"),
        )

    def test_the_export_matches_the_bank_file(self):
        export = self._create_ktb_export()
        text, records = self._render(export)
        self.assertNotEqual(
            text, "Demo Text File. You must config `Bank Export Format` First."
        )
        header, details, trailer = records[0], records[1:-1], records[-1]

        self.assertRecordMatches(
            header, self.sample[0], HEADER, HEADER_VARIABLE, "header"
        )
        self.assertEqual(len(details), len(PAYEES))
        for idx, (produced, expected) in enumerate(zip(details, self.sample[1:-1])):
            self.assertRecordMatches(
                produced, expected, DETAIL, (), "detail %s" % (idx + 1)
            )
        # Nothing variable: the file is whole, so its trailer describes its own
        # body and ours has to say the same thing.
        self.assertRecordMatches(trailer, self.sample[-1], TRAILER, (), "trailer")

        self.assertEqual(
            self._slice(header, HEADER, "Effective Date"),
            export.effective_date.strftime("%d%m%y"),
        )
        self.assertSingleByteEncoding(export)

    def test_the_money_must_leave_from_an_account_at_this_bank(self):
        """A KTB file that debits an account at another bank is refused.

        KTB reads the header's Sending A/C as one of its own, so a file
        addressed to KTB carrying an SCB account asks it to debit an account it
        has never heard of. It came back rejected with nothing said about which
        account, because as far as the bank was concerned it was not there.
        """
        bank_scb = self._thai_bank("SICOTHBK", "014", "Siam Commercial Bank")
        journal_scb = self._paying_journal(bank_scb, "0883000059", "TWRG")
        payee = self._payee("สมชาย  ทดสอบระบบ", self.bank_ktb, "6930009999")
        wrong_bank = self._posted_payment(journal_scb, payee, 100.00)
        export = self._export_with_lines(
            {
                "bank": "KRTHTHBK",
                "bank_export_format_id": self.bank_export_format.id,
                "ktb_sender_name": SENDER_NAME,
                "ktb_bank_type": "direct",
                "ktb_service_type_direct": "14",
                "effective_date": fields.Date.today(),
            },
            wrong_bank,
        )
        with self.assertRaises(UserError):
            export.action_confirm()

    def test_a_payee_bank_without_a_clearing_code_is_refused(self):
        """The D record names the payee's bank by its three-digit code.

        With none, the field went out as three spaces and KTB refused the file.
        The codes are seeded but under ``noupdate``, so a database that had the
        bank records first still has them empty.
        """
        export = self._create_ktb_export()
        self.bank_ktb.bank_code = False
        with self.assertRaises(UserError):
            export.action_confirm()

    def test_every_record_is_128_characters(self):
        _text, records = self._render(self._create_ktb_export())
        for record in records:
            self.assertEqual(len(record), 128, repr(record))
