# Copyright 2024 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError

from odoo.addons.l10n_th_bank_payment_export.tests.common import CommonBankPaymentExport


class TestBankPaymentExportKBANK(CommonBankPaymentExport):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format = cls.bank_export_format_model.search(
            [("bank", "=", "KASITHBK")], limit=1
        )

    def _create_kbank_export(self):
        bank_payment = self.bank_payment_export_model.create(
            {
                "name": "/",
                "bank": "KASITHBK",
                "bank_export_format_id": self.bank_export_format.id,
                "kbank_company_id": "000001",
                "kbank_sender_name": "KMITL",
                "kbank_service_type": "04",
                "effective_date": fields.Date.today(),
            }
        )
        bank_payment.action_get_all_payments()
        for line in bank_payment.export_line_ids:
            if not line.payment_partner_bank_id:
                line.payment_partner_bank_id = line.payment_partner_id.bank_ids[:1].id
            # K-Cash Connect Plus requires a 10-digit account number
            line.payment_partner_bank_id.acc_number = "1234567890"
        return bank_payment

    def test_01_account_number_must_be_10_digits(self):
        bank_payment = self._create_kbank_export()
        bank_payment.export_line_ids[0].payment_partner_bank_id.acc_number = "12345"
        with self.assertRaises(UserError):
            bank_payment.action_confirm()

    def test_02_kbank_export_record_length(self):
        bank_payment = self._create_kbank_export()
        self.assertTrue(bank_payment.export_line_ids)
        bank_payment.action_confirm()
        text = bank_payment._export_bank_payment_text_file()
        self.assertNotEqual(
            text, "Demo Text File. You must config `Bank Export Format` First."
        )
        records = [rec for rec in text.split("\r\n") if rec]
        # Layout reconstructed from the real KMITL sample: N space-delimited
        # detail records followed by a single trailer (there is no header).
        details, trailer = records[:-1], records[-1]
        # One detail record per exported payment line.
        self.assertEqual(len(details), len(bank_payment.export_line_ids))
        for idx, detail in enumerate(details):
            # Running number: 6-digit, sequential from 1.
            self.assertEqual(detail[:6], str(idx + 1).zfill(6))
            # Record code 7106 marks a detail record.
            self.assertEqual(detail[7:11], "7106")
            # Fixed part before the variable-length name field is 103 chars.
            self.assertGreaterEqual(len(detail), 103)
        # Trailer: 53 chars, code 9100, record count = number of details.
        self.assertEqual(len(trailer), 53)
        self.assertEqual(trailer[7:11], "9100")
        self.assertEqual(trailer[:6], str(len(details)).zfill(6))
        # The file must encode cleanly to the bank's TIS-620/cp874 encoding.
        text.encode("cp874")
