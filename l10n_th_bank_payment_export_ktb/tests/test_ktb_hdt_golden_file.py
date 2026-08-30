# Copyright 2026 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The KTB Direct Credit (H/D/T) layout, against the file KMITL sends the bank.

``tests/fixtures/ktb_hdt_sample.txt`` is that file, trimmed by KMITL to one of
its 1,199 details; only the account numbers were replaced, keeping their length
and leading digits. Everything else is the bank's, including the detail's
41,222,000.29 -- which is what pins the amount field at 13 characters, a width
nothing else available states.

The other KTB product, ``ktb_ipay``, has no sample and is not covered here.
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
    ("Amount", 13, DIGITS),
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

HEADER_VARIABLE = ("Effective Date",)
TRAILER_VARIABLE = ("Total Record Count", "Transaction Count", "Total Amount")

SENDING_ACCOUNT = "0280000001"
SENDER_NAME = "KING MONGKUT LADGRABANG"
PAYEE_ACCOUNT = "6630000001"
PAYEE_AMOUNT = 41222000.29


@tagged("post_install", "-at_install")
class TestKtbHdtGoldenFile(CommonBankExportFormat):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format = cls.env.ref("l10n_th_bank_payment_export_ktb.ktb_hdt")
        cls.bank_ktb = cls._thai_bank("KRTHTHBK", "006", "Krung Thai Bank")
        cls.journal_ktb = cls._paying_journal(cls.bank_ktb, SENDING_ACCOUNT, "TKTB")
        payee = cls._payee("สมชาย  ทดสอบระบบ", cls.bank_ktb, PAYEE_ACCOUNT)
        cls.payments = cls._posted_payment(cls.journal_ktb, payee, PAYEE_AMOUNT)
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
        header, detail, trailer = self.sample
        self.assertRecordShape(header, HEADER, "sample header")
        self.assertRecordShape(detail, DETAIL, "sample detail")
        self.assertRecordShape(trailer, TRAILER, "sample trailer")

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
        self.assertEqual(len(details), 1)
        self.assertRecordMatches(details[0], self.sample[1], DETAIL, (), "detail")
        self.assertRecordMatches(
            trailer, self.sample[2], TRAILER, TRAILER_VARIABLE, "trailer"
        )

        self.assertEqual(
            self._slice(header, HEADER, "Effective Date"),
            export.effective_date.strftime("%d%m%y"),
        )
        # The trailer counts the header and itself, which is why the bank's file
        # ends at 001201 for 1,199 transactions.
        self.assertEqual(self._slice(trailer, TRAILER, "Total Record Count"), "000003")
        self.assertEqual(self._slice(trailer, TRAILER, "Transaction Count"), "000001")
        self.assertEqual(self._slice(trailer, TRAILER, "Total Amount"), "0004122200029")
        self.assertSingleByteEncoding(export)

    def test_every_record_is_128_characters(self):
        _text, records = self._render(self._create_ktb_export())
        for record in records:
            self.assertEqual(len(record), 128, repr(record))
