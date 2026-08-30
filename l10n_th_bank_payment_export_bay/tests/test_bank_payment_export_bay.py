# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The BAY CashLink layout, against the file KMITL sends the bank.

``tests/fixtures/bay_cashlink_sample.txt`` is that file. Every byte position,
every field width and every fill character is the bank's; what was replaced is
the identities -- account numbers keep their length and leading digits, payee
names are Thai strings of exactly the byte length the originals had, so no
record changes width. Amounts, dates, counts and totals are the bank's own,
which is what lets the satang arithmetic and the trailer relationships be
checked here at all.

Two repairs to the sample, both from the trimming that cut it from 117 details
down to two: the second detail was 127 characters because its amount had lost a
leading zero (both details carry the same 10,000.00, and the first proves the
width), and there were two empty lines at the end.
"""

from odoo import fields

from odoo.addons.l10n_th_bank_payment_export_format.tests.common import (
    BLANK,
    DIGITS,
    TEXT,
    CommonBankExportFormat,
)
from odoo.tests.common import tagged

HEADER = (
    ("Record ID", 3, "507"),
    ("Originator ID", 3, "001"),
    ("File Date", 6, DIGITS),
    ("Originator Acct/Ref", 10, DIGITS),
    ("Sender Name", 20, BLANK),
    ("Code", 3, "712"),
    ("Reserved", 27, BLANK),
    ("Type Code", 4, "A001"),
    ("Value Period", 4, DIGITS),
    ("Detail Count", 7, DIGITS),
    ("Grand Total", 15, DIGITS),
    ("Filler", 26, BLANK),
)

DETAIL = (
    ("Record ID", 3, "507"),
    ("Originator ID", 3, "001"),
    ("Receiving Account", 10, DIGITS),
    ("Payee Name", 20, TEXT),
    ("Amount", 11, DIGITS),
    ("Filler", 26, BLANK),
    ("Originator ID (detail)", 3, "001"),
    ("Value Period (detail)", 4, DIGITS),
    ("Filler (tail)", 48, BLANK),
)

# The sample was trimmed, so its counts and totals describe a body that is not
# in it; and its date is in the past, which the export refuses.
HEADER_VARIABLE = ("File Date", "Value Period", "Detail Count", "Grand Total")
DETAIL_VARIABLE = ("Value Period (detail)",)

PAYEES = (
    ("6580000001", "ทดสอบ  ระบบจ่ายเงิน", 10000.00),
    ("5070000002", "สมศรี  ทดสอบระบบโอน", 10000.00),
)


@tagged("post_install", "-at_install")
class TestBankPaymentExportBAY(CommonBankExportFormat):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format = cls.env.ref(
            "l10n_th_bank_payment_export_bay.bay_cashlink"
        )
        cls.bank_bay = cls._thai_bank("AYUDTHBK", "002", "Bank of Ayudhya")
        cls.journal_bay = cls._paying_journal(cls.bank_bay, "5070000001", "TBAY")
        cls.payments = cls.env["account.payment"]
        for acc_number, name, amount in PAYEES:
            payee = cls._payee(name, cls.bank_bay, acc_number)
            cls.payments |= cls._posted_payment(cls.journal_bay, payee, amount)
        cls.sample = cls._load_fixture(
            "l10n_th_bank_payment_export_bay", "bay_cashlink_sample.txt"
        )

    def _create_bay_export(self):
        return self._export_with_lines(
            {
                "bank": "AYUDTHBK",
                "bank_export_format_id": self.bank_export_format.id,
                "effective_date": fields.Date.today(),
            },
            self.payments,
        )

    def test_the_sample_still_matches_the_layout(self):
        """Guards the evidence: a re-trimmed fixture proves nothing."""
        header, details = self.sample[0], self.sample[1:]
        self.assertRecordShape(header, HEADER, "sample header")
        self.assertEqual(len(details), 2)
        for idx, detail in enumerate(details):
            self.assertRecordShape(detail, DETAIL, "sample detail %s" % (idx + 1))

    def test_the_export_matches_the_bank_file(self):
        export = self._create_bay_export()
        text, records = self._render(export)
        self.assertNotEqual(
            text, "Demo Text File. You must config `Bank Export Format` First."
        )
        header, details = records[0], records[1:]

        self.assertRecordMatches(
            header, self.sample[0], HEADER, HEADER_VARIABLE, "header"
        )
        self.assertEqual(len(details), len(self.payments))
        for produced, expected, idx in zip(details, self.sample[1:], range(2)):
            self.assertRecordMatches(
                produced, expected, DETAIL, DETAIL_VARIABLE, "detail %s" % (idx + 1)
            )

        # What the sample cannot speak for, checked against this file instead.
        period = export.effective_date.strftime("%m%y")
        self.assertEqual(
            self._slice(header, HEADER, "File Date"),
            export.effective_date.strftime("%d%m%y"),
        )
        self.assertEqual(self._slice(header, HEADER, "Value Period"), period)
        self.assertEqual(self._slice(header, HEADER, "Detail Count"), "0000002")
        self.assertEqual(self._slice(header, HEADER, "Grand Total"), "000000002000000")
        for detail in details:
            self.assertEqual(
                self._slice(detail, DETAIL, "Value Period (detail)"), period
            )
        self.assertSingleByteEncoding(export)

    def test_every_record_is_128_characters(self):
        """The one thing CashLink gives no leeway on."""
        _text, records = self._render(self._create_bay_export())
        for record in records:
            self.assertEqual(len(record), 128, repr(record))
