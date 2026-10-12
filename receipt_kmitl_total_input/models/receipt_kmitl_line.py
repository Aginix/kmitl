# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ReceiptKmitlLine(models.Model):
    _inherit = "kmitl.receipt.line"

    amount = fields.Monetary(inverse="_inverse_amount")

    def _inverse_amount(self):
        for line in self:
            quantity = line.quantity or 1.0
            line.price_unit = line.amount / quantity
            if not line.quantity:
                line.quantity = quantity
