# Copyright 2026 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The SCB BCM layout, against the file KMITL sends the bank.

``tests/fixtures/scb_bcm_sample.txt`` is that file, trimmed by KMITL to three of
its 560 credits. Account numbers were replaced keeping their length and their
first four digits, because SCB carries the branch in the first three of them and
the fourth is the account type -- both are read back out of the number by this
layout. Payee names are Thai strings of the byte lengths the originals had.

Two things the sample cannot settle, and this file does not pretend to:

* the checksum on the first line. SCB's file opens with 40 uppercase hex
  characters, which is the shape of a SHA-1, but the sample is trimmed so the
  digest is over a body we do not have and cannot be reproduced. What is checked
  here is the shape, and that our own digest is a digest of what we actually
  wrote. Whether SCB hashes the body the way we do has to come from the bank.
* the 005 and 006 records (withholding tax, invoice detail). The sample carries
  neither, and no other file we have does.
"""

import hashlib

from odoo import fields

from odoo.addons.l10n_th_bank_payment_export_format.tests.common import (
    BLANK,
    DIGITS,
    TEXT,
    CommonBankExportFormat,
)
from odoo.tests.common import tagged

HEADER = (
    ("Record Type", 3, "001"),
    ("Company Id", 12, TEXT),
    ("Customer Reference", 32, TEXT),
    ("Message/File Date", 8, DIGITS),
    ("Message/File Time", 6, DIGITS),
    ("Channel Id", 3, "BCM"),
    ("Batch Reference", 32, TEXT),
)

DEBIT = (
    ("Record Type", 3, "002"),
    ("Product Code", 3, "PAY"),
    ("Value Date", 8, DIGITS),
    ("Debit Account No", 25, TEXT),
    ("Account Type of Debit Account", 2, DIGITS),
    ("Debit Branch Code", 4, DIGITS),
    ("Debit Currency", 3, "THB"),
    ("Debit Amount", 16, DIGITS),
    ("Internal Reference", 8, DIGITS),
    ("No. of Credits", 6, DIGITS),
    ("Fee Debit Account", 15, TEXT),
    ("Filler", 9, BLANK),
    ("Media Clearing Cycle", 1, BLANK),
    ("Account Type (Fee)", 2, DIGITS),
    ("Debit Branch Code (Fee)", 4, DIGITS),
)

CREDIT = (
    ("Record Type", 3, "003"),
    ("Credit Sequence Number", 6, DIGITS),
    ("Credit Account", 25, TEXT),
    ("Credit Amount", 16, DIGITS),
    ("Credit Currency", 3, "THB"),
    ("Internal Reference", 8, DIGITS),
    ("WHT Present", 1, "N"),
    ("Invoice Details Present", 1, "N"),
    ("Credit Advice Required", 1, "N"),
    ("Delivery Mode", 1, BLANK),
    ("Pickup Location", 4, BLANK),
    ("WHT Form Type", 2, DIGITS),
    ("WHT Tax Running No.", 14, BLANK),
    ("WHT Attach No.", 6, DIGITS),
    ("No. of WHT Details", 2, DIGITS),
    ("Total WHT Amount", 16, DIGITS),
    ("No. of Invoice Details", 6, DIGITS),
    ("Total Invoice Amount", 16, DIGITS),
    ("WHT Pay Type", 1, DIGITS),
    ("WHT Remark", 40, BLANK),
    ("WHT Deduct Date", 8, BLANK),
    ("Receiving Bank Code", 3, "014"),
    ("Receiving Bank Name", 35, BLANK),
    ("Receiving Branch Code", 4, DIGITS),
    ("Receiving Branch Name", 35, BLANK),
    ("WHT Signatory", 1, BLANK),
    ("Beneficiary Notification", 1, BLANK),
    ("Customer Reference Number", 20, BLANK),
    ("Cheque Reference Document Type", 1, BLANK),
    ("Payment Type Code", 3, BLANK),
    ("ServicesType", 2, BLANK),
    ("Remark", 50, BLANK),
    ("SCB Remark", 18, BLANK),
    ("Beneficiary Charge", 2, BLANK),
)

PAYEE = (
    ("Record Type", 3, "004"),
    ("Internal Reference", 8, DIGITS),
    ("Credit Sequence Number", 6, DIGITS),
    ("Payee1 IDCard", 15, BLANK),
    ("Payee1 Name (Thai)", 100, TEXT),
    ("Payee1 Address 1 - 3", 210, BLANK),
    ("Payee1 Tax ID", 10, BLANK),
    ("Payee1 Name (English)", 70, BLANK),
    ("Payee1 Fax Number", 10, BLANK),
    ("Payee1 Mobile Phone Number", 10, BLANK),
    ("Payee1 E-mail Address", 64, BLANK),
    ("Payee2 Name (Thai)", 100, BLANK),
    ("Payee2 Address 1", 70, BLANK),
    ("Payee2 Address 2", 70, BLANK),
    ("Payee2 Address 3", 70, BLANK),
)

TRAILER = (
    ("Record Type", 3, "999"),
    ("Total No. of Debits", 6, "000001"),
    ("Total No. of Credits", 6, DIGITS),
    ("Total Amount", 16, DIGITS),
)

# The file's own references and the moment it was made; and the counts and
# totals of the 557 credits that were trimmed out of the sample.
HEADER_VARIABLE = (
    "Customer Reference",
    "Message/File Date",
    "Message/File Time",
    "Batch Reference",
)
DEBIT_VARIABLE = ("Value Date", "Debit Amount", "No. of Credits")
TRAILER_VARIABLE = ("Total No. of Credits", "Total Amount")

COMPANY_ID = "kmit088"
DEBIT_ACCOUNT = "0883000001"
PAYEES = (
    ("0880000001", "นางสาวสมหญิง  ทดสอบ", 1681.25),
    ("0880000002", "สมชาย  ทดสอบระบบ", 63288.00),
    ("0880000003", "สมศรี  ทดสอบระบบโอน", 19884.75),
)


@tagged("post_install", "-at_install")
class TestScbBcmGoldenFile(CommonBankExportFormat):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format = cls.env.ref(
            "l10n_th_bank_payment_export_scb.scb_domestic"
        )
        cls.bank_scb = cls._thai_bank("SICOTHBK", "014", "Siam Commercial Bank")
        cls.journal_scb = cls._paying_journal(cls.bank_scb, DEBIT_ACCOUNT, "TSCB")
        cls.payments = cls.env["account.payment"]
        for acc_number, name, amount in PAYEES:
            payee = cls._payee(name, cls.bank_scb, acc_number)
            cls.payments |= cls._posted_payment(cls.journal_scb, payee, amount)
        cls.sample = cls._load_fixture(
            "l10n_th_bank_payment_export_scb", "scb_bcm_sample.txt"
        )

    def _create_scb_export(self):
        return self._export_with_lines(
            {
                "bank": "SICOTHBK",
                "bank_export_format_id": self.bank_export_format.id,
                "scb_company_id": COMPANY_ID,
                "scb_product_code": "PAY",
                "effective_date": fields.Date.today(),
            },
            self.payments,
        )

    def test_the_sample_still_matches_the_layout(self):
        checksum, header, debit = self.sample[0], self.sample[1], self.sample[2]
        self.assertEqual(len(checksum), 40)
        self.assertRecordShape(header, HEADER, "sample header")
        self.assertRecordShape(debit, DEBIT, "sample debit")
        # 003 / 004 / 003 / 004 / 003 -- the third credit's payee record went
        # with the trimming.
        for idx, offset in enumerate((3, 5, 7)):
            self.assertRecordShape(
                self.sample[offset], CREDIT, "sample credit %s" % (idx + 1)
            )
        for idx, offset in enumerate((4, 6)):
            self.assertRecordShape(
                self.sample[offset], PAYEE, "sample payee %s" % (idx + 1)
            )
        self.assertRecordShape(self.sample[8], TRAILER, "sample trailer")

    def test_the_export_matches_the_bank_file(self):
        export = self._create_scb_export()
        text, records = self._render(export)
        self.assertNotEqual(
            text, "Demo Text File. You must config `Bank Export Format` First."
        )
        # checksum, 001, 002, then a 003/004 pair per credit, then 999.
        self.assertEqual(len(records), 4 + 2 * len(PAYEES))

        self.assertRecordMatches(
            records[1], self.sample[1], HEADER, HEADER_VARIABLE, "header"
        )
        self.assertRecordMatches(
            records[2], self.sample[2], DEBIT, DEBIT_VARIABLE, "debit"
        )
        for idx, offset in enumerate((3, 5, 7)):
            self.assertRecordMatches(
                records[offset],
                self.sample[offset],
                CREDIT,
                (),
                "credit %s" % (idx + 1),
            )
        for idx, offset in enumerate((4, 6)):
            self.assertRecordMatches(
                records[offset],
                self.sample[offset],
                PAYEE,
                (),
                "payee %s" % (idx + 1),
            )
        self.assertRecordMatches(
            records[-1], self.sample[8], TRAILER, TRAILER_VARIABLE, "trailer"
        )

        # SCB amounts are the value times a thousand, not in satang.
        self.assertEqual(
            self._slice(records[2], DEBIT, "Debit Amount"), "0000000084854000"
        )
        self.assertEqual(self._slice(records[2], DEBIT, "No. of Credits"), "000003")
        self.assertEqual(
            self._slice(records[2], DEBIT, "Value Date"),
            export.effective_date.strftime("%Y%m%d"),
        )
        self.assertEqual(
            self._slice(records[-1], TRAILER, "Total No. of Credits"), "000003"
        )
        self.assertEqual(
            self._slice(records[-1], TRAILER, "Total Amount"), "0000000084854000"
        )
        self.assertSingleByteEncoding(export)

    def test_the_receiving_branch_comes_from_the_payee_account(self):
        """SCB carries the branch in the first three digits of the account.

        A branch code held on the bank record would be one branch for the whole
        of SCB, and misroute every payee who banks anywhere else -- silently,
        because a well-formed code for the wrong branch looks like a right one.
        """
        export = self._create_scb_export()
        line = export.export_line_ids[0]
        line.payment_partner_bank_id.acc_number = "1112223334"
        _text, records = self._render(export)
        self.assertEqual(
            self._slice(records[3], CREDIT, "Receiving Branch Code"), "0111"
        )

    def test_the_file_opens_with_a_checksum_of_its_own_body(self):
        """Shape, and self-consistency -- which is as far as the sample goes.

        The sample's digest covers 560 credits we do not have, so it cannot be
        recomputed. What can be checked is that the 40 characters we write are a
        SHA-1 of the bytes that follow them, in the encoding the layout uses.
        """
        export = self._create_scb_export()
        text, _records = self._render(export)
        checksum, body = text.split("\r\n", 1)
        self.assertEqual(len(checksum), 40)
        self.assertEqual(checksum, checksum.upper())
        self.assertTrue(all(char in "0123456789ABCDEF" for char in checksum))
        self.assertEqual(
            checksum,
            hashlib.sha1(body.encode("cp874")).hexdigest().upper(),
        )
