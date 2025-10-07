# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatchLine(models.Model):
    _name = 'account.asset.batch.line'
    _inherit = "analytic.mixin"
    _description = 'AccountAssetBatchLine'

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        tracking=True,
        domain=[],
    )

    name = fields.Char(
        string="Asset Name", 
        related='product_id.display_name',
        required=True,
        tracking=True,
        store=True
    )

    sequence = fields.Integer(
        default=1
    )
    
    batch_id = fields.Many2one(
        "account.asset.batch",
        required=True,
        index=True
    )

    account_fiscal_year_id = fields.Many2one(
        related='batch_id.account_fiscal_year_id'
    )

    purchase_id = fields.Many2one(
        "purchase.order"
    )

    gpsc_id = fields.Many2one(
        "procurement.gpsc",
        string="GPSC Number",
        required=True,
        tracking=True
    )

    operating_unit_id = fields.Many2one(
        "operating.unit",
        related="batch_id.operating_unit_id",
    )

    profile_id = fields.Many2one(
        "account.asset.profile",
        string="Asset Profile",
        required=True,
        tracking=True
    )

    amount = fields.Integer(
        string="Amount",
        required=True,
        tracking=True
    )

    price_per_unit = fields.Float(
        required=True,
        tracking=True
    )

    amount_total = fields.Float(
        string = "Total",
        compute="_compute_amount_total",
        tracking=True
    )

    notes = fields.Text()

    @api.depends("product_id")
    def _compute_name(self):
        for line in self:
            line.name = line.product_id.display_name or ""

    @api.depends("amount", "price_per_unit")
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = rec.amount * rec.price_per_unit

    def _onchange_batch_id(self):
        for line in self:
            if line.batch_id and line.batch_id.purchase_id:
                po_products = line.batch_id.purchase_id.order_line.mapped("product_id").ids
                return {"domain": {"product_id": [("id", "in", po_products)]}}
            return {"domain": {"product_id": []}}
        
    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and line.batch_id and line.batch_id.purchase_id:
                po_line = self.env["purchase.order.line"].search([
                    ("order_id", "=", line.batch_id.purchase_id.id),
                    ("product_id", "=", line.product_id.id)
                ], limit=1)
                if po_line:
                    line.price_per_unit = po_line.price_unit
                    line.amount = po_line.product_qty

    def unlink(self):
        for line in self:
            assets = self.env["account.asset"].search([("batch_line_id", "=", line.id)])
            if assets:
                raise UserError(_("Cannot delete a line already linked to assets."))
        return super().unlink()