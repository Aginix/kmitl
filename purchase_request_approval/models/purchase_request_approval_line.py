# -*- coding: utf-8 -*-
from odoo import fields, models


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
    estimated_cost = fields.Float(string="Estimated Cost")
