# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ReceiptKmitl(models.Model):
    _inherit = "kmitl.receipt"

    invoice_id = fields.Many2one(
        "kmitl.invoice",
        string="Invoice",
        readonly=True,
        copy=False,
        index=True,
        help="The invoice this receipt settles. Its entry credits the customer's "
        "receivable account instead of revenue.",
    )

    @api.constrains("invoice_id", "amount_total")
    def _check_invoice_amount(self):
        """An invoice is paid in full or not at all: the books reconcile its single
        debit against these credits, and a part payment would leave it half settled
        while the department sees it paid."""
        for rec in self.filtered("invoice_id"):
            invoice = rec.invoice_id.sudo()
            if rec.currency_id.compare_amounts(rec.amount_total, invoice.amount_total):
                raise ValidationError(
                    _(
                        "Receipt %(receipt)s must collect the full amount of invoice "
                        "%(invoice)s (%(amount)s)."
                    )
                    % {
                        "receipt": rec.name,
                        "invoice": invoice.name,
                        "amount": "{:,.2f}".format(invoice.amount_total),
                    }
                )

    def _prepare_move_vals(self, line_vals):
        vals = super()._prepare_move_vals(line_vals)
        if self.invoice_id:
            vals["kmitl_invoice_id"] = self.invoice_id.id
        return vals

    def _prepare_move_line_vals(self, line):
        # Always through super(): other add-ons (operating unit) stamp this hook too,
        # and which of them is loaded last is not pinned.
        vals = super()._prepare_move_line_vals(line)
        if self.invoice_id:
            vals["account_id"] = self.invoice_id._get_receivable_account().id
        return vals

    def action_cancel(self):
        res = super().action_cancel()
        self._release_invoice()
        return res

    def _release_invoice(self):
        """The receipt no longer settles its invoice: issue the invoice again, so the
        debtor can be receipted afresh."""
        for rec in self.filtered("invoice_id"):
            invoice = rec.invoice_id.sudo()
            invoice.write({"state": "issued", "receipt_id": False})
            rec.invoice_id = False
            rec.message_post(
                body=_("Invoice %s is issued again; this receipt no longer settles it.")
                % invoice.name
            )
            invoice.message_post(
                body=_("Receipt %s was cancelled; the invoice is issued again.")
                % rec.name
            )


class ReceiptRemittance(models.Model):
    _inherit = "kmitl.receipt.remittance"

    def action_draft(self):
        """Resetting a posted remittance reverses the receipts' entries, and with
        them what settled an invoice in the books: the invoice must not stay paid.

        Its receipt is cancelled, through the normal path that detaches it from the
        remittance, rather than left a draft: a draft that kept its invoice could be
        posted again while the invoice is receipted a second time.
        """
        settling = (
            self.filtered(lambda rec: rec.state == "posted")
            .sudo()
            .receipt_ids.filtered("invoice_id")
        )
        res = super().action_draft()
        settling.action_cancel()
        return res
