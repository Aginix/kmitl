# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ReceiptRefundLine(models.Model):
    _name = "receipt.kmitl.refund.line"
    _description = "Receipt Refund Line"
    _order = "refund_id, id"

    refund_id = fields.Many2one(
        "receipt.kmitl.refund",
        required=True,
        ondelete="cascade",
    )
    receipt_line_id = fields.Many2one(
        "receipt.kmitl.line",
        string="Receipt Line",
        required=True,
    )
    name = fields.Char(
        related="receipt_line_id.name",
        store=True,
        readonly=True,
    )
    original_amount = fields.Monetary(
        related="receipt_line_id.amount",
        store=True,
        currency_field="currency_id",
        readonly=True,
    )
    amount = fields.Monetary(
        string="Refund Amount",
        required=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="refund_id.currency_id",
        store=True,
        readonly=True,
    )
