# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class BankPaymentExportTextConfirm(models.TransientModel):
    """Show what is about to go to the bank before the file is written.

    Exporting cannot be undone, and the browser confirmation the base puts on
    the button is a fixed sentence: it cannot say how much money the file moves.
    This dialog does, so the amount is read once more at the last moment it can
    still be stopped.
    """

    _name = "bank.payment.export.text.confirm"
    _description = "Confirm Export Text File"

    payment_export_id = fields.Many2one(
        comodel_name="bank.payment.export",
        string="e-Payment File",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    paying_account_id = fields.Many2one(
        related="payment_export_id.paying_account_id",
    )
    effective_date = fields.Date(
        related="payment_export_id.effective_date",
    )
    export_line_count = fields.Integer(
        related="payment_export_id.export_line_count",
    )
    total_amount = fields.Monetary(
        related="payment_export_id.total_amount",
        string="Total Transfer Amount",
    )
    currency_id = fields.Many2one(
        related="payment_export_id.currency_id",
    )

    def action_export(self):
        self.ensure_one()
        return self.payment_export_id.action_export_text_file()
