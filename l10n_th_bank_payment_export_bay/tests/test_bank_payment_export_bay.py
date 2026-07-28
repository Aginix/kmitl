# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields

from odoo.addons.l10n_th_bank_payment_export.tests.common import CommonBankPaymentExport


class TestBankPaymentExportBAY(CommonBankPaymentExport):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bank_export_format = cls.bank_export_format_model.search(
            [("bank", "=", "AYUDTHBK")], limit=1
        )

    def _create_bay_export(self):
        bank_payment = self.bank_payment_export_model.create(
            {
                "name": "/",
                "bank": "AYUDTHBK",
                "bank_export_format_id": self.bank_export_format.id,
                "bay_sender_name": "KMITL",
                "effective_date": fields.Date.today(),
            }
        )
        bank_payment.action_get_all_payments()
        for line in bank_payment.export_line_ids:
            if not line.payment_partner_bank_id:
                line.payment_partner_bank_id = line.payment_partner_id.bank_ids[:1].id
            line.payment_partner_bank_id.acc_number = "1234567890"
        return bank_payment

    def test_bay_export_record_length(self):
        """The layout was reconstructed from the real KMITL sample (testBOA):
        one 128-byte header + N 128-byte detail records, no trailer, every
        record prefixed with ``507`` + ``001``.
        """
        bank_payment = self._create_bay_export()
        self.assertTrue(bank_payment.export_line_ids)
        bank_payment.action_confirm()
        text = bank_payment._export_bank_payment_text_file()
        self.assertNotEqual(
            text, "Demo Text File. You must config `Bank Export Format` First."
        )
        records = [rec for rec in text.split("\r\n") if rec]
        header, details = records[0], records[1:]
        # Header: fixed-width 128, 507+001 prefix.
        self.assertEqual(len(header), 128)
        self.assertEqual(header[:6], "507001")
        # One detail per exported payment line, each fixed-width 128.
        self.assertEqual(len(details), len(bank_payment.export_line_ids))
        for detail in details:
            self.assertEqual(len(detail), 128)
            self.assertEqual(detail[:6], "507001")
        # The file must encode cleanly to the bank's TIS-620/cp874 encoding.
        text.encode("cp874")
