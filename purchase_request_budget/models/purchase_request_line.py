# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    analytic_distribution = fields.Json(
        'Analytic',
        compute="_compute_analytic_distribution", store=True, copy=True, readonly=False,
        related='request_id.analytic_distribution'
    )

    @api.onchange("product_id")
    def onchange_product_id(self):
        pass

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

    def _compute_default_product_id(self):
        super()._compute_default_product_id()
        for rec in self:
            rec.product_id = rec.request_id.budget_account_id.product_id
