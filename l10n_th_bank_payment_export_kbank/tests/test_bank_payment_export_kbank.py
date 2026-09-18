# Copyright 2024 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The KBANK K-Cash Connect Plus layout, against the file KMITL sends the bank.

``tests/fixtures/kbank_ccp_sample.txt`` is that file, trimmed by KMITL to two of
its 214 details and then masked here: account numbers keep their length and
leading digits, and the two payee names are Thai strings of exactly the byte
lengths the originals had -- 20 and 22 -- because that is the point of this
layout. K-Cash Connect Plus writes the name as it is and ends the record 25
characters later, so its records are 123 and 125 characters, and a beneficiary
name padded to any fixed width would be wrong.
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

DETAIL_PREFIX = (
    ("Running Number", 6, DIGITS),
    ("Separator", 1, BLANK),
    ("Record Code", 4, "7106"),
    ("Separator (2)", 1, BLANK),
    ("Originator Code", 7, DIGITS),
    ("Separator (3)", 1, BLANK),
    ("Beneficiary Account", 10, DIGITS),
    ("Separator (4)", 1, BLANK),
    ("Amount", 15, DIGITS),
    ("Separator (5)", 1, BLANK),
    ("Effective Date", 6, DIGITS),
    ("Separator (6)", 1, BLANK),
    ("Title", 24, TEXT),
)
DETAIL_SUFFIX = (("Reserved", 25, BLANK),)
FIXED_PART = 78 + 25

TRAILER = (
    ("Record Count", 6, DIGITS),
    ("Separator", 1, BLANK),
    ("Record Code", 4, "9100"),
    ("Separator (2)", 1, BLANK),
    ("Originator Code", 7, DIGITS),
    ("Separator (3)", 1, BLANK),
    ("Account", 10, "0000000000"),
    ("Separator (4)", 1, BLANK),
    ("Grand Total", 15, DIGITS),
    ("Separator (5)", 1, BLANK),
    ("Date Field", 6, "000000"),
)

DETAIL_VARIABLE = ("Effective Date",)
TRAILER_VARIABLE = ("Record Count", "Grand Total")

ORIGINATOR_CODE = "0360016"
PAYEES = (
    ("0360000001", "สมบัติ  ทดสอบระบบงาน", "นส.", 10000.00),
    ("6310000001", "ปิติ  ทดสอบระบบโอนเงิน", "นาง", 10000.00),
)


def detail_spec(record):
    """The record's own spec: everything is fixed but the name."""
    return (
        DETAIL_PREFIX
        + (("Beneficiary Name", len(record) - FIXED_PART, TEXT),)
        + DETAIL_SUFFIX
    )


@tagged("post_install", "-at_install")
class TestBankPaymentExportKBANK(CommonBankExportFormat):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format = cls.env.ref(
            "l10n_th_bank_payment_export_kbank.kbank_ccp"
        )
        cls.bank_kbank = cls._thai_bank("KASITHBK", "004", "Kasikorn Bank")
        cls.journal_kbank = cls._paying_journal(cls.bank_kbank, "0360000009", "TKBK")
        cls.payments = cls.env["account.payment"]
        for acc_number, name, shortcut, amount in PAYEES:
            payee = cls._payee(
                name, cls.bank_kbank, acc_number, title=cls._thai_title(shortcut)
            )
            cls.payments |= cls._posted_payment(cls.journal_kbank, payee, amount)
        cls.sample = cls._load_fixture(
            "l10n_th_bank_payment_export_kbank", "kbank_ccp_sample.txt"
        )

    def _create_kbank_export(self):
        return self._export_with_lines(
            {
                "bank": "KASITHBK",
                "bank_export_format_id": self.bank_export_format.id,
                "kbank_company_id": ORIGINATOR_CODE,
                "kbank_sender_name": "KING MONGKUT LADGRABANG",
                "kbank_service_type": "04",
                "effective_date": fields.Date.today(),
            },
            self.payments,
        )

    def test_the_sample_still_matches_the_layout(self):
        details, trailer = self.sample[:-1], self.sample[-1]
        self.assertEqual([len(rec) for rec in details], [123, 125])
        for idx, detail in enumerate(details):
            self.assertRecordShape(
                detail, detail_spec(detail), "sample detail %s" % (idx + 1)
            )
        self.assertRecordShape(trailer, TRAILER, "sample trailer")

    def test_the_export_matches_the_bank_file(self):
        export = self._create_kbank_export()
        text, records = self._render(export)
        self.assertNotEqual(
            text, "Demo Text File. You must config `Bank Export Format` First."
        )
        details, trailer = records[:-1], records[-1]

        self.assertEqual(len(details), len(self.payments))
        for produced, expected, idx in zip(details, self.sample[:-1], range(2)):
            self.assertRecordMatches(
                produced,
                expected,
                detail_spec(expected),
                DETAIL_VARIABLE,
                "detail %s" % (idx + 1),
            )
        self.assertRecordMatches(
            trailer, self.sample[-1], TRAILER, TRAILER_VARIABLE, "trailer"
        )

        effective = export.effective_date.strftime("%y%m%d")
        for detail in details:
            self.assertEqual(
                self._slice(detail, detail_spec(detail), "Effective Date"), effective
            )
        self.assertEqual(self._slice(trailer, TRAILER, "Record Count"), "000002")
        self.assertEqual(
            self._slice(trailer, TRAILER, "Grand Total"), "000000002000000"
        )
        self.assertSingleByteEncoding(export)

    def test_the_name_field_carries_no_width_of_its_own(self):
        """Two payees, two different name lengths, two record lengths.

        A padded name field would make both records the same length and match
        neither of the bank's.
        """
        _text, records = self._render(self._create_kbank_export())
        self.assertEqual([len(rec) for rec in records[:-1]], [123, 125])
        self.assertEqual(len(records[-1]), 53)

    def test_account_number_must_be_10_digits(self):
        export = self._create_kbank_export()
        export.export_line_ids[0].payment_partner_bank_id.acc_number = "12345"
        with self.assertRaises(UserError):
            export.action_confirm()
