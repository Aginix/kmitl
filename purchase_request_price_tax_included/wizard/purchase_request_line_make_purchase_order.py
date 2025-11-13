import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import get_lang

_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"
    bypass_warning = True

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        res = super()._prepare_purchase_order_line(po, item)
        res["price_unit"] = item.price_unit
        res["taxes_id"] = (
            [(4, item.line_id.tax_id.id)] if item.line_id.tax_id else False
        )
        return res

    @api.model
    def _prepare_item(self, line):
        res = super()._prepare_item(line)
        res["price_unit"] = line.price_unit
        res["tax_id"] = line.tax_id.id if line.tax_id else False
        return res


class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"
    bypass_warning = True

    price_unit = fields.Float(
        string="Unit Price",
        required=True,
        digits="Product Price",
    )

    estimated_cost = fields.Monetary(compute="_compute_amount")
    price_subtotal = fields.Monetary(compute="_compute_amount", string="Subtotal")
    price_total = fields.Monetary(compute="_compute_amount", string="Total")
    price_tax = fields.Float(compute="_compute_amount", string="Tax")

    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        related="request_id.tax_id",
    )

    @api.depends("product_qty", "price_unit", "tax_id")
    def _compute_amount(self):
        for line in self:
            tax_results = self.env["account.tax"]._compute_taxes(
                [line._convert_to_tax_base_line_dict()]
            )
            totals = list(tax_results["totals"].values())[0]
            amount_untaxed = totals["amount_untaxed"]
            amount_tax = totals["amount_tax"]

            line.update(
                {
                    "price_subtotal": amount_untaxed,
                    "price_tax": amount_tax,
                    "price_total": amount_untaxed + amount_tax,
                    "estimated_cost": amount_untaxed + amount_tax,
                }
            )

    def _convert_to_tax_base_line_dict(self):
        """Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env["account.tax"]._convert_to_tax_base_line_dict(
            self,
            partner=None,
            currency=self.request_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_qty,
            price_subtotal=self.price_subtotal,
        )
