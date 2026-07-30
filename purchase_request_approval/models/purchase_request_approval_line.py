# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseRequestApprovalLine(models.Model):
    _name = "purchase.request.approval.line"
    _description = "Purchase Request Approval Line"

    approval_id = fields.Many2one(
        comodel_name="purchase.request.approval",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one("product.product")
    name = fields.Text(string="Description")
    product_qty = fields.Float(string="Quantity")
    product_uom_id = fields.Many2one("uom.uom", string="UoM")
    price_unit = fields.Float(string="Unit Price")
    currency_id = fields.Many2one(related="approval_id.currency_id")
    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        related="approval_id.tax_id",
        store=True,
    )
    estimated_cost = fields.Monetary(compute="_compute_amount", store=True)
    price_subtotal = fields.Monetary(
        compute="_compute_amount", string="Subtotal", store=True
    )
    price_total = fields.Monetary(
        compute="_compute_amount", string="Total", store=True
    )
    price_tax = fields.Float(compute="_compute_amount", string="Tax", store=True)

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
        self.ensure_one()
        return self.env["account.tax"]._convert_to_tax_base_line_dict(
            self,
            partner=None,
            currency=self.approval_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.price_unit,
            quantity=self.product_qty,
            price_subtotal=self.price_subtotal,
        )
