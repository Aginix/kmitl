# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptLifecycle(ReceiptKmitlCommon):
    def test_to_submit_assigns_number_no_move(self):
        receipt = self._make_receipt()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.amount_total, 5000.0)

        receipt.action_to_submit()
        self.assertEqual(receipt.state, "to_submit")
        self.assertFalse(receipt.move_id)
        fy_be = str(receipt._get_fy_be())
        self.assertTrue(receipt.name.startswith("RC/%s/" % fy_be))

    def test_post_creates_move(self):
        receipt = self._make_receipt(
            lines=[(self.product_tuition, 1, 5000.0), (self.product_card, 2, 100.0)]
        )
        receipt.action_to_submit()
        receipt._action_post()

        self.assertEqual(receipt.state, "done")
        self.assertTrue(receipt.move_id)
        self.assertEqual(receipt.move_id.state, "posted")

        debit_lines = receipt.move_id.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(debit_lines.account_id, self.cash_account)
        self.assertEqual(sum(debit_lines.mapped("debit")), 5200.0)

        credit_lines = receipt.move_id.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(
            set(credit_lines.mapped("account_id")),
            {self.income_tuition, self.income_other},
        )
        self.assertEqual(sum(credit_lines.mapped("credit")), 5200.0)

    def test_post_uses_payment_method_account(self):
        receipt = self._make_receipt(method=self.pm_transfer)
        receipt.action_to_submit()
        receipt._action_post()
        debit_lines = receipt.move_id.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(debit_lines.account_id, self.bank_account)
        self.assertEqual(receipt.move_id.journal_id, self.bank_journal)

    def test_cancel_only_from_draft(self):
        receipt = self._make_receipt()
        receipt.action_to_submit()
        with self.assertRaises(UserError):
            receipt.action_cancel()
        receipt.action_draft()
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")

    def test_cannot_unlink_non_cancelled(self):
        receipt = self._make_receipt()
        receipt.action_to_submit()
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

    def test_reset_to_draft_from_to_submit(self):
        receipt = self._make_receipt()
        receipt.action_to_submit()
        name = receipt.name
        receipt.action_draft()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.name, name)

    def test_reset_blocked_while_remitted(self):
        receipt = self._make_receipt()
        receipt.action_to_submit()
        self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [receipt.id])],
            }
        )
        with self.assertRaises(UserError):
            receipt.action_draft()
