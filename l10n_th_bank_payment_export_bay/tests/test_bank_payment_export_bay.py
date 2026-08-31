# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The BAY CashLink layout, against a whole file KMITL sent the bank.

``tests/fixtures/bay_cashlink_sample.txt`` is that file: a header and all 46 of
its details, nothing trimmed, every record 128 characters. Because it is whole,
its header's detail count and grand total are the ones its own body adds up to,
so the test reproduces them rather than skipping over them.

What was replaced is the identities: account numbers keep their length and their
branch prefix, and every payee name is a synthetic Thai string of exactly the
byte length the original had. That last part matters more here than anywhere
else -- fifteen of the forty-six names fill all twenty characters of the field
because the bank's own file cut them there, and a name that arrived one byte
longer used to push the rest of the record out and make it 129.
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

# Only the dates: the export refuses an effective date in the past, and the
# file's is May 2026. Everything else, counts and total included, is ours to
# reproduce.
HEADER_VARIABLE = ("File Date", "Value Period")
DETAIL_VARIABLE = ("Value Period (detail)",)

SENDING_ACCOUNT = "5070000001"
# Appended to one payee whose name already fills the field, so the render has to
# cut it back to exactly what the bank's file holds.
OVERFLOW = "เกินความกว้างของช่อง"


@tagged("post_install", "-at_install")
class TestBankPaymentExportBAY(CommonBankExportFormat):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format = cls.env.ref(
            "l10n_th_bank_payment_export_bay.bay_cashlink"
        )
        cls.bank_bay = cls._thai_bank("AYUDTHBK", "002", "Bank of Ayudhya")
        cls.journal_bay = cls._paying_journal(cls.bank_bay, SENDING_ACCOUNT, "TBAY")
        cls.sample = cls._load_fixture(
            "l10n_th_bank_payment_export_bay", "bay_cashlink_sample.txt"
        )
        details = cls.sample[1:]
        # The first payee whose name already fills the field is the one given a
        # longer name than the field can hold.
        cls.overflow_index = next(
            idx for idx, rec in enumerate(details) if rec[35] != " "
        )
        cls.payments = cls.env["account.payment"]
        for idx, record in enumerate(details):
            name = record[16:36].rstrip(" ")
            if idx == cls.overflow_index:
                name += OVERFLOW
            payee = cls._payee(name, cls.bank_bay, record[6:16])
            cls.payments |= cls._posted_payment(
                cls.journal_bay, payee, int(record[36:47]) / 100.0
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
        self.assertEqual(len(self.sample), 47)
        self.assertRecordShape(self.sample[0], HEADER, "sample header")
        for idx, record in enumerate(self.sample[1:]):
            self.assertRecordShape(record, DETAIL, "sample detail %s" % (idx + 1))

    def test_the_header_adds_up_to_the_details(self):
        details = self.sample[1:]
        total = sum(int(self._slice(rec, DETAIL, "Amount")) for rec in details)
        self.assertEqual(
            self._slice(self.sample[0], HEADER, "Grand Total"),
            str(total).rjust(15, "0"),
        )
        self.assertEqual(
            self._slice(self.sample[0], HEADER, "Detail Count"),
            str(len(details)).rjust(7, "0"),
        )

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
        self.assertEqual(len(details), len(self.sample) - 1)
        for idx, (produced, expected) in enumerate(zip(details, self.sample[1:])):
            self.assertRecordMatches(
                produced, expected, DETAIL, DETAIL_VARIABLE, "detail %s" % (idx + 1)
            )

        period = export.effective_date.strftime("%m%y")
        self.assertEqual(
            self._slice(header, HEADER, "File Date"),
            export.effective_date.strftime("%d%m%y"),
        )
        self.assertEqual(self._slice(header, HEADER, "Value Period"), period)
        for detail in details:
            self.assertEqual(
                self._slice(detail, DETAIL, "Value Period (detail)"), period
            )
        self.assertSingleByteEncoding(export)

    def test_a_name_longer_than_the_field_is_cut_to_it(self):
        """One payee is deliberately given more name than CashLink allows.

        The record still has to come out 128 characters, with the name cut to
        exactly what the bank's own file holds.
        """
        export = self._create_bay_export()
        _text, records = self._render(export)
        produced = records[1 + self.overflow_index]
        self.assertEqual(len(produced), 128)
        self.assertEqual(
            self._slice(produced, DETAIL, "Payee Name"),
            self._slice(self.sample[1 + self.overflow_index], DETAIL, "Payee Name"),
        )

    def test_every_record_is_128_characters(self):
        """The one thing CashLink gives no leeway on."""
        _text, records = self._render(self._create_bay_export())
        for record in records:
            self.assertEqual(len(record), 128, repr(record))
