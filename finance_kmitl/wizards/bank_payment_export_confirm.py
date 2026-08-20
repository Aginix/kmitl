# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class BankPaymentExportConfirm(models.TransientModel):
    """Ask what happened, at the moment the file is closed.

    The office confirms a file as a whole rather than row by row, so this press
    says "every payee has their money" for twenty payees at once. Where that is
    not the plain truth — the bank could not credit one of them and the officer
    paid them another way — this is the only place it gets written down.
    """

    _name = "bank.payment.export.confirm"
    _description = "Confirm Transfer Succeeded"

    payment_export_id = fields.Many2one(
        comodel_name="bank.payment.export",
        string="e-Payment File",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    note = fields.Text(
        string="Note",
        help="Optional. Most files go through as sent and there is nothing to say. "
        "Write here what the bank could not do and how it was settled instead.",
    )

    def action_confirm(self):
        self.ensure_one()
        return self.payment_export_id._confirm_epayment_success(note=self.note)
