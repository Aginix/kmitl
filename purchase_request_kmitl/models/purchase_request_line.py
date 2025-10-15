# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    name = fields.Text(string="Description", tracking=True)

    @api.onchange("product_id")
    def onchange_product_id(self):
        pass

    @api.depends("request_id")
    def _compute_default_product_id(self):
        for rec in self:
            rec.product_id = rec.product_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        product_id = self.env.context.get("default_product_id")
        if product_id:
            product = self.env["product.product"].browse(product_id)
            res.update({
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "name": product.display_name,
            })
        return res
