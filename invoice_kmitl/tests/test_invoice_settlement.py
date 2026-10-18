# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged

from .common import InvoiceKmitlCommon


@tagged("post_install", "-at_install")
class TestInvoiceSettlement(InvoiceKmitlCommon):
    def _issue_and_collect(self, **extra):
        """An issued invoice whose debtor has paid: it and its draft receipt."""
        invoice = self._make_invoice(**extra)
        self._issue(invoice)
        invoice.action_receive_payment()
        return invoice, invoice.receipt_id

    def _remit(self, receipt):
        """Take the receipt through a remittance, up to its draft journal entry."""
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "approver_id": self.approver.id,
                "receipt_ids": [Command.set(receipt.ids)],
            }
        )
        remittance.action_submit()
        remittance.action_approve()
        remittance.action_post()
        return remittance

    def test_receive_payment_drafts_a_receipt_for_the_customer(self):
        # A source other than the receipt's default one, to see it carried across.
        invoice, receipt = self._issue_and_collect(
            source_analytic_id=self.source_b.id
        )
        self.assertEqual(invoice.state, "paid")
        self.assertEqual(receipt.state, "draft")
        self.assertEqual(receipt.invoice_id, invoice)
        self.assertEqual(receipt.partner_id, self.customer)
        self.assertFalse(receipt.is_walkin)
        self.assertEqual(receipt.amount_total, invoice.amount_total)
        for name in (
            "department_analytic_id",
            "source_analytic_id",
            "fund_analytic_id",
            "activity_analytic_id",
        ):
            self.assertEqual(receipt[name], invoice[name])
        # Paid for the department; the books do not know yet.
        self.assertEqual(invoice.payment_state, "not_paid")

    def test_payment_needs_a_live_receivable_entry(self):
        invoice = self._make_invoice()
        self._issue(invoice)
        # Accounting deleted the draft on its own side.
        invoice.move_id.with_context(force_delete=True).unlink()
        with self.assertRaises(UserError):
            invoice.action_receive_payment()

    def test_receipt_must_collect_the_invoice_in_full(self):
        invoice, receipt = self._issue_and_collect()
        with self.assertRaises(ValidationError):
            receipt.line_ids.write({"price_unit": 1.0})
            receipt.amount_total  # noqa: B018 - the recompute runs the constraint

    def test_cancelling_the_receipt_issues_the_invoice_again(self):
        invoice, receipt = self._issue_and_collect()
        receipt.action_cancel()
        self.assertEqual(receipt.state, "cancelled")
        self.assertEqual(invoice.state, "issued")
        self.assertFalse(invoice.receipt_id)
        self.assertFalse(receipt.invoice_id)

    def test_posting_the_receipt_entry_reconciles_the_receivable(self):
        invoice, receipt = self._issue_and_collect(
            lines=[(self.product_tuition, 1, 5000.0), (self.product_card, 2, 100.0)]
        )
        self._post(invoice.move_id)
        self._remit(receipt)

        entry = receipt.move_id
        self.assertEqual(entry.kmitl_invoice_id, invoice)
        # One credit per receipt line against the invoice's single debit, all on the
        # account the invoice's own entry was booked to.
        credits = entry.line_ids.filtered(
            lambda line: line.credit and line.account_id == self.receivable
        )
        self.assertEqual(len(credits), 2)
        self.assertEqual(invoice.move_id.payment_state, "not_paid")

        self._post(entry)
        self.assertEqual(invoice.move_id.payment_state, "paid")
        self.assertEqual(invoice.amount_residual, 0.0)
        self.assertTrue(all(credits.mapped("reconciled")))

    def test_the_entry_posted_last_triggers_the_reconciliation(self):
        invoice, receipt = self._issue_and_collect()
        self._remit(receipt)
        # The receipt's entry goes first: its counterpart is still a draft.
        self._post(receipt.move_id)
        self.assertEqual(invoice.move_id.payment_state, "not_paid")
        self._post(invoice.move_id)
        self.assertEqual(invoice.move_id.payment_state, "paid")

    def test_resetting_a_posted_remittance_issues_the_invoice_again(self):
        invoice, receipt = self._issue_and_collect()
        self._post(invoice.move_id)
        remittance = self._remit(receipt)
        remittance.action_draft()
        self.assertEqual(invoice.state, "issued")
        self.assertFalse(invoice.receipt_id)
        self.assertEqual(receipt.state, "cancelled")
        self.assertFalse(receipt.remittance_id)
