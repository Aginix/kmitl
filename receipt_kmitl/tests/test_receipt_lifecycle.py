# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import ReceiptKmitlCommon


@tagged("post_install", "-at_install")
class TestReceiptLifecycle(ReceiptKmitlCommon):
    def test_create_mints_number_no_move(self):
        receipt = self._make_receipt()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.amount_total, 5000.0)
        self.assertFalse(receipt.move_id)
        fy_be = str(receipt._get_fy_be())
        self.assertTrue(receipt.name.startswith("RC/%s/" % fy_be))

    def test_post_creates_move(self):
        receipt = self._make_receipt(
            lines=[(self.product_tuition, 1, 5000.0), (self.product_card, 2, 100.0)]
        )
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
        receipt._action_post()
        debit_lines = receipt.move_id.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(debit_lines.account_id, self.bank_account)
        self.assertEqual(receipt.move_id.journal_id, self.bank_journal)

    def test_cancel_only_from_draft(self):
        receipt = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [receipt.id])],
            }
        )
        remittance.action_submit()
        self.assertEqual(receipt.state, "submitted")
        with self.assertRaises(UserError):
            receipt.action_cancel()
        remittance.action_cancel()
        self.assertEqual(receipt.state, "draft")
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")

    def test_cannot_unlink_non_cancelled(self):
        receipt = self._make_receipt()
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

    def test_reset_to_draft_from_cancelled(self):
        receipt = self._make_receipt()
        name = receipt.name
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")
        receipt.action_draft()
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.name, name)

    def test_reset_to_draft_blocked_from_submitted(self):
        receipt = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [receipt.id])],
            }
        )
        remittance.action_submit()
        with self.assertRaises(UserError):
            receipt.action_draft()

    def test_reset_blocked_while_remitted(self):
        receipt = self._make_receipt()
        self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [receipt.id])],
            }
        )
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")
        with self.assertRaises(UserError):
            receipt.action_draft()

    def test_constrains_requires_at_least_one_line(self):
        with self.assertRaises(ValidationError):
            self.env["kmitl.receipt"].create(
                {
                    "department_analytic_id": self.dept_a.id,
                    "payment_method_id": self.pm_cash.id,
                    "partner_id": self.walkin.id,
                }
            )

    def test_constrains_requires_positive_total(self):
        with self.assertRaises(ValidationError):
            self._make_receipt(lines=[(self.product_tuition, 1, 0.0)])

    def test_payment_type_defaults_to_cash(self):
        receipt = self._make_receipt()
        self.assertEqual(receipt.payment_type, "cash")

    def test_payment_type_cheque_requires_number_and_date(self):
        with self.assertRaises(ValidationError):
            self._make_receipt(extra_vals={"payment_type": "cheque"})

    def test_payment_type_cheque_with_fields_ok(self):
        receipt = self._make_receipt(
            extra_vals={
                "payment_type": "cheque",
                "cheque_number": "123456",
                "cheque_date": fields.Date.context_today(self.env.user),
            }
        )
        self.assertEqual(receipt.payment_type, "cheque")

    def test_payment_type_transfer_requires_date(self):
        with self.assertRaises(ValidationError):
            self._make_receipt(extra_vals={"payment_type": "transfer"})

    def test_payment_type_transfer_with_date_ok(self):
        receipt = self._make_receipt(
            extra_vals={
                "payment_type": "transfer",
                "transfer_date": fields.Date.context_today(self.env.user),
            }
        )
        self.assertEqual(receipt.payment_type, "transfer")

    def test_onchange_payment_type_clears_inactive_fields(self):
        receipt = self.env["kmitl.receipt"].new(
            {
                "department_analytic_id": self.dept_a.id,
                "payment_type": "cheque",
                "cheque_number": "123456",
                "cheque_date": fields.Date.context_today(self.env.user),
                "payment_method_id": self.pm_cash.id,
            }
        )
        receipt.payment_type = "cash"
        receipt._onchange_payment_type()
        self.assertFalse(receipt.cheque_number)
        self.assertFalse(receipt.cheque_date)
        self.assertFalse(receipt.payment_method_id)
