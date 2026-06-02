# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class ReceiptKmitlLine(models.Model):
    _name = "receipt.kmitl.line"
    _description = "KMITL Receipt Line"
    _inherit = ["analytic.distribution.mixin"]
    _order = "receipt_id, sequence, id"

    receipt_id = fields.Many2one(
        "receipt.kmitl",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Description", required=True)
    receipt_type_id = fields.Many2one(
        "receipt.kmitl.type",
        string="Receipt Type",
        required=True,
    )
    suspense_account_id = fields.Many2one(
        "account.account",
        string="Suspense Account",
        required=True,
        domain="[('deprecated', '=', False)]",
    )
    quantity = fields.Float(default=1.0, required=True, digits="Product Unit of Measure")
    price_unit = fields.Monetary(required=True, currency_field="currency_id")
    amount = fields.Monetary(
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="receipt_id.currency_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        related="receipt_id.state",
        store=True,
        readonly=True,
    )
    allocation_line_id = fields.Many2one(
        "receipt.kmitl.allocation.line",
        string="Allocation Line",
        readonly=True,
        copy=False,
    )
    income_account_id = fields.Many2one(
        "account.account",
        related="allocation_line_id.income_account_id",
        string="Income Account (allocated)",
        store=True,
        readonly=True,
    )

    @api.depends("quantity", "price_unit")
    def _compute_amount(self):
        for line in self:
            line.amount = (line.quantity or 0.0) * (line.price_unit or 0.0)

    @api.onchange("receipt_type_id")
    def _onchange_receipt_type_id(self):
        for line in self:
            if line.receipt_type_id and not line.suspense_account_id:
                line.suspense_account_id = line.receipt_type_id.suspense_account_id
