# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import InvoiceKmitlCommon


@tagged("post_install", "-at_install")
class TestInvoiceFlow(InvoiceKmitlCommon):
    def test_numbering_and_dimensions(self):
        first = self._make_invoice()
        second = self._make_invoice()
        self.assertTrue(first.name.startswith("IV/"))
        self.assertNotEqual(first.name, second.name)
        # The header's dimensions reach the line.
        self.assertTrue(first.analytic_distribution)
        self.assertEqual(
            first.line_ids.analytic_distribution, first.analytic_distribution
        )

    def test_all_four_dimensions_are_required(self):
        with mute_logger("odoo.sql_db"), self.assertRaises(
            IntegrityError
        ), self.env.cr.savepoint():
            self._make_invoice(fund_analytic_id=False)

    def test_due_date_cannot_precede_the_invoice_date(self):
        with self.assertRaises(ValidationError):
            self._make_invoice(
                date_due=fields.Date.context_today(self.env.user) - timedelta(days=1)
            )

    def test_submission_raises_a_plain_untaxed_receivable_entry(self):
        invoice = self._make_invoice(
            lines=[(self.product_tuition, 1, 5000.0), (self.product_card, 2, 100.0)]
        )
        submission = self._issue(invoice)
        self.assertEqual(submission.state, "done")
        self.assertTrue(submission.name.startswith("IS/"))
        self.assertEqual(invoice.state, "issued")

        move = invoice.move_id
        self.assertEqual(move.move_type, "out_invoice")
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.journal_id, self.ar_journal)
        self.assertEqual(move.ref, invoice.name)
        self.assertEqual(move.kmitl_invoice_id, invoice)
        # Dated as the invoice is, not as the day the entry is posted.
        self.assertEqual(move.invoice_date, invoice.date)
        self.assertEqual(move.invoice_date_due, invoice.date_due)
        self.assertFalse(move.invoice_payment_term_id)
        self.assertFalse(move.invoice_line_ids.tax_ids)
        # One receivable line, the only one amount_residual is read from.
        receivable = move.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        self.assertEqual(len(receivable), 1)
        self.assertEqual(receivable.account_id, self.receivable)
        self.assertEqual(move.amount_total, 5200.0)
        self.assertEqual(move.amount_total, invoice.amount_total)

    def test_issuing_needs_a_receivable_account(self):
        self.customer.property_account_receivable_id = False
        with self.assertRaises(UserError):
            self._issue(self._make_invoice())

    def test_accounting_can_submit_what_treasury_raised(self):
        invoice = self._make_invoice()
        self._issue(invoice)
        maker_vals = {
            "name": "Maker",
            "login": "kmitl_invoice_maker",
            "groups_id": [
                Command.set(
                    [self.env.ref("accounting_kmitl.group_accounting_kmitl_user").id]
                )
            ],
        }
        if self.ou:
            maker_vals["operating_unit_ids"] = [Command.link(self.ou.id)]
        maker = self.env["res.users"].create(maker_vals)
        plain = self.env["account.move"].create(
            {"move_type": "entry", "journal_id": self.cash_journal.id}
        )
        self.assertTrue(invoice.move_id.with_user(maker).can_submit)
        # The creator rule still holds for an entry nobody raised for an invoice.
        self.assertFalse(plain.with_user(maker).can_submit)

    def test_cancelling_an_issued_invoice_deletes_a_draft_entry(self):
        invoice = self._make_invoice()
        self._issue(invoice)
        move = invoice.move_id
        invoice.action_cancel()
        self.assertEqual(invoice.state, "cancelled")
        self.assertFalse(invoice.move_id)
        self.assertFalse(move.exists())

    def test_cancelling_a_posted_entry_reverses_it(self):
        invoice = self._make_invoice()
        self._issue(invoice)
        self._post(invoice.move_id)
        invoice.action_cancel()
        refund = invoice.refund_move_id
        self.assertEqual(invoice.state, "cancelled")
        self.assertEqual(refund.move_type, "out_refund")
        self.assertEqual(refund.state, "draft")
        # Posting the credit note reconciles it against the original.
        self._post(refund)
        self.assertEqual(invoice.move_id.payment_state, "reversed")
        self.assertEqual(invoice.amount_residual, 0.0)

    def test_a_paid_invoice_cannot_be_cancelled(self):
        invoice = self._make_invoice()
        self._issue(invoice)
        invoice.action_receive_payment()
        with self.assertRaises(UserError):
            invoice.action_cancel()

    def test_reset_submission_drops_its_cancelled_invoices(self):
        keep, drop = self._make_invoice(), self._make_invoice()
        submission = self._issue(keep | drop)
        drop.action_cancel()
        submission.action_draft()
        self.assertEqual(submission.invoice_ids, keep)
        self.assertEqual(keep.state, "draft")
        # The cancelled invoice no longer stands in the way of the next Submit.
        submission.action_submit()
        self.assertEqual(keep.state, "submitted")

    def test_reset_of_a_sent_submission_takes_the_draft_entries_back(self):
        invoice = self._make_invoice()
        submission = self._issue(invoice)
        move = invoice.move_id
        submission.action_draft()
        self.assertEqual(submission.state, "draft")
        self.assertEqual(invoice.state, "draft")
        self.assertFalse(invoice.move_id)
        self.assertFalse(move.exists())
