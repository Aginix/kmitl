# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptLifecycle(ReceiptKmitlCommon):
    def test_issue_creates_posted_move(self):
        receipt = self._make_receipt()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.amount_total, 5000.0)

        receipt.action_issue()
        self.assertEqual(receipt.state, "issued")
        self.assertTrue(receipt.move_id)
        self.assertEqual(receipt.move_id.state, "posted")

        # Sequence assigned
        self.assertNotEqual(receipt.name, "/")
        self.assertTrue(receipt.name.startswith("RC/01/"))

        # JE: Dr Cash / Cr Suspense
        debit_lines = receipt.move_id.line_ids.filtered(lambda l: l.debit > 0)
        credit_lines = receipt.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_lines.account_id, self.cash_account)
        self.assertEqual(sum(debit_lines.mapped("debit")), 5000.0)
        self.assertEqual(credit_lines.account_id, self.suspense_edu)
        self.assertEqual(sum(credit_lines.mapped("credit")), 5000.0)

    def test_issue_requires_lines(self):
        receipt = self.env["receipt.kmitl"].create(
            {
                "department_id": self.dept_a.id,
                "journal_id": self.cash_journal.id,
                "payment_method": "cash",
                "partner_id": self.walkin.id,
            }
        )
        with self.assertRaises(Exception):
            receipt.action_issue()

    def test_cancel_before_deposit(self):
        receipt = self._make_receipt()
        receipt.action_issue()
        original_name = receipt.name

        receipt._apply_cancel("Test cancel reason", self.env.user)
        self.assertEqual(receipt.state, "cancelled")
        # Name preserved (no gap in sequence)
        self.assertEqual(receipt.name, original_name)
        # Reverse JE created
        reverse = self.env["account.move"].search(
            [("ref", "ilike", "Cancellation of %s" % original_name)]
        )
        self.assertTrue(reverse)
        self.assertEqual(reverse.state, "posted")

    def test_cannot_unlink_issued(self):
        receipt = self._make_receipt()
        receipt.action_issue()
        with self.assertRaises(UserError):
            receipt.unlink()

    def test_partner_snapshot_freezes_on_issue(self):
        partner = self.env["res.partner"].create(
            {"name": "Original Name", "vat": "1234567890"}
        )
        receipt = self.env["receipt.kmitl"].create(
            {
                "department_id": self.dept_a.id,
                "journal_id": self.cash_journal.id,
                "payment_method": "cash",
                "partner_id": partner.id,
                "customer_name": "Original Name",
                "customer_tax_id": "1234567890",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "receipt_type_id": self.type_edu.id,
                            "name": "test",
                            "suspense_account_id": self.suspense_edu.id,
                            "quantity": 1,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )
        receipt.action_issue()

        partner.write({"name": "Changed Later"})
        self.assertEqual(receipt.customer_name, "Original Name")
