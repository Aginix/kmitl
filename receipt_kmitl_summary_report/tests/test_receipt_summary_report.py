# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.receipt_kmitl.tests.common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptSummaryReport(ReceiptKmitlCommon):
    def test_payment_type_filter_uses_receipt_field(self):
        cash_receipt = self._make_receipt()
        transfer_receipt = self._make_receipt(method=self.pm_transfer)
        today = str(fields.Date.context_today(self.env.user))
        report = self.env["receipt_kmitl.receipt.report"]
        result = report.get_report_data(
            {"date_from": today, "date_to": today, "payment_type": "transfer"}
        )
        row_ids = {r["id"] for group in result["groups"] for r in group["rows"]}
        self.assertEqual(row_ids, {transfer_receipt.id})
        self.assertNotIn(cash_receipt.id, row_ids)

    def test_get_filter_lines_has_no_other_payment_type(self):
        report = self.env["receipt_kmitl.receipt.report"]
        lines = report.get_filter_lines({"payment_type": "other"})
        self.assertFalse(any("Other" in line for line in lines))
