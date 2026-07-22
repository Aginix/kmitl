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
        # First record is the HDCT header (178 chars); the rest are D details (487)
        self.assertEqual(records[0][:4], "HDCT")
        self.assertEqual(len(records[0]), 178)
        for detail in records[1:]:
            self.assertEqual(detail[0], "D")
            self.assertEqual(len(detail), 487)
        # Number of detail records equals the number of exported payment lines
        self.assertEqual(len(records) - 1, len(bank_payment.export_line_ids))
