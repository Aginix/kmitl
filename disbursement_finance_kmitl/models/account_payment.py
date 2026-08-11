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
