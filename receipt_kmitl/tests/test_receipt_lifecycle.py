# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptLifecycle(ReceiptKmitlCommon):
    def test_confirm_assigns_number_no_move(self):
        receipt = self._make_receipt()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.amount_total, 5000.0)

        receipt.action_confirm()
        self.assertEqual(receipt.state, "confirmed")
        # No journal entry at confirm time
        self.assertFalse(receipt.move_id)
        # Sequence assigned per fiscal year: RC/<fy4>/nnnn
        fy_be = str(receipt._get_fy_be())
        self.assertTrue(receipt.name.startswith("RC/%s/" % fy_be))

    def test_post_creates_move(self):
        receipt = self._make_receipt(
            lines=[(self.product_tuition, 1, 5000.0), (self.product_card, 2, 100.0)]
        )
        receipt.action_confirm()
        receipt.action_post()

        self.assertEqual(receipt.state, "posted")
        self.assertTrue(receipt.move_id)
        self.assertEqual(receipt.move_id.state, "posted")

        # Dr payment-method cash account = total
        debit_lines = receipt.move_id.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(debit_lines.account_id, self.cash_account)
        self.assertEqual(sum(debit_lines.mapped("debit")), 5200.0)

        # Cr income per line
        credit_lines = receipt.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(
            set(credit_lines.mapped("account_id")),
            {self.income_tuition, self.income_other},
        )
        self.assertEqual(sum(credit_lines.mapped("credit")), 5200.0)

    def test_post_uses_payment_method_account(self):
        receipt = self._make_receipt(method=self.pm_transfer)
        receipt.action_confirm()
        receipt.action_post()
        debit_lines = receipt.move_id.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(debit_lines.account_id, self.bank_account)
        self.assertEqual(receipt.move_id.journal_id, self.bank_journal)

    def test_cannot_post_before_confirm(self):
        receipt = self._make_receipt()
        with self.assertRaises(UserError):
            receipt.action_post()

    def test_cancel_keeps_number(self):
        receipt = self._make_receipt()
        receipt.action_confirm()
        name = receipt.name
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")
        self.assertEqual(receipt.name, name)
        self.assertFalse(receipt.move_id)

    def test_cannot_unlink_posted(self):
        receipt = self._make_receipt()
        receipt.action_confirm()
        receipt.action_post()
        with self.assertRaises(UserError):
            receipt.unlink()

    def test_header_analytic_syncs_to_lines(self):
        receipt = self._make_receipt()
        line = receipt.line_ids[0]
        self.assertTrue(line.analytic_distribution)
        self.assertIn(str(self.dept_a.id), line.analytic_distribution)

        receipt.write({"department_analytic_id": self.dept_b.id})
        self.assertIn(str(self.dept_b.id), line.analytic_distribution)
        self.assertNotIn(str(self.dept_a.id), line.analytic_distribution)

    def test_action_correct_reopens_detached_receipt(self):
        receipt = self._make_receipt()
        receipt.action_confirm()
        name = receipt.name

        receipt.action_correct()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.name, name)

        receipt.action_confirm()
        self.assertEqual(receipt.name, name)

    def test_action_correct_blocked_while_remitted(self):
        receipt = self._make_receipt()
        receipt.action_confirm()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [receipt.id])],
            }
        )
        self.assertTrue(remittance)
        with self.assertRaises(UserError):
            receipt.action_correct()
