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
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        domain="[('property_account_income_id', '!=', False)]",
    )
    name = fields.Char(string="Description", required=True)
    account_id = fields.Many2one(
        "account.account",
        string="Income Account",
        required=True,
        domain="[('deprecated', '=', False), ('account_type', '=', 'income')]",
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

    @api.depends("quantity", "price_unit")
    def _compute_amount(self):
        for line in self:
            line.amount = (line.quantity or 0.0) * (line.price_unit or 0.0)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if not line.product_id:
                continue
            product = line.product_id
            if not line.name:
                line.name = product.display_name
            line.account_id = (
                product.property_account_income_id
                or product.categ_id.property_account_income_categ_id
            )
            if not line.price_unit:
                line.price_unit = product.lst_price
