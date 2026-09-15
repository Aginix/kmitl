# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseContractLine(models.Model):
    _name = "purchase.contract.line"
    _description = "Purchase Contract Line (revision snapshot)"

    contract_id = fields.Many2one(
        "purchase.contract",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)

    # Mirror of purchase.order.line
    product_id = fields.Many2one("product.product", required=True)
    name = fields.Text(string="Description", required=True)
    product_qty = fields.Float(string="Quantity", required=True, default=1.0)
    product_uom = fields.Many2one("uom.uom", string="Unit of Measure")
    price_unit = fields.Float(string="Unit Price", required=True, default=0.0)
    taxes_id = fields.Many2many("account.tax", string="Taxes")
    analytic_distribution = fields.Json(string="Analytic Distribution")

    # Reference to the live PO line this snapshot was created from (nullable —
    # newly added lines during a revision have no source line yet).
    source_order_line_id = fields.Many2one(
        "purchase.order.line",
        ondelete="set null",
        help="The purchase.order.line this snapshot was cloned from, if any.",
    )

    currency_id = fields.Many2one(
        related="contract_id.currency_id",
        store=True,
        readonly=True,
    )
    subtotal = fields.Monetary(
        compute="_compute_subtotal",
        store=True,
    )

    @api.depends("product_qty", "price_unit")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (line.product_qty or 0.0) * (line.price_unit or 0.0)
