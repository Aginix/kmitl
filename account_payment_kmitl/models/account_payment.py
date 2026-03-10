# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    kmitl_payment_type_id = fields.Many2one(
        comodel_name="kmitl.payment.type",
        string="Payment Type (KMITL)",
    )

    def action_submit(self):
        """Submit payment for approval. Delegates to account.move."""
        self.move_id.action_submit()

    @api.onchange("kmitl_payment_type_id")
    def _onchange_kmitl_payment_type_id(self):
        if self.kmitl_payment_type_id:
            self.payment_type = self.kmitl_payment_type_id.direction
            if self.kmitl_payment_type_id.journal_id:
                self.journal_id = self.kmitl_payment_type_id.journal_id

    @api.depends("kmitl_payment_type_id")
    def _compute_destination_account_id(self):
        super()._compute_destination_account_id()
        for pay in self:
            ptype = pay.kmitl_payment_type_id
            if ptype and ptype.override_account_id:
                pay.destination_account_id = ptype.override_account_id

    def _get_trigger_fields_to_synchronize(self):
        return (
            *super()._get_trigger_fields_to_synchronize(),
            "kmitl_payment_type_id",
        )
