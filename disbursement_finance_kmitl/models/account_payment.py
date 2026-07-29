# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    disbursement_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        ondelete="set null",
        index=True,
        copy=False,
    )

    def action_submit(self):
        """Create the cheque-register row at submit for DR cheque payments.

        Non-DR cheque payments get their register row when they post (the
        original behaviour). In the disbursement workflow posting happens last
        (clearing), while the physical cheque must be numbered, printed and
        handed over long before that — so the row is needed as soon as the
        payment is submitted. ``_create_cheque_register_entries`` skips
        payments that already have a row, so the on-post hook stays a no-op.
        """
        res = super().action_submit()
        self.filtered(
            lambda p: p.disbursement_request_id
            and p.kmitl_payment_type_id.is_cheque
        )._create_cheque_register_entries()
        return res
