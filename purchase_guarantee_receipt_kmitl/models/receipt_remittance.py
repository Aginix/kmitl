# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ReceiptRemittance(models.Model):
    _inherit = "kmitl.receipt.remittance"

    receipt_kind = fields.Selection(
        selection_add=[("guarantee", "Guarantee")],
        ondelete={"guarantee": "set default"},
    )
