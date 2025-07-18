# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    product_id = fields.Many2one(
        compute="_compute_default_product_id",
        store=True,
        readonly=False,
    )

    @api.depends("request_id")
    def _compute_default_product_id(self):
        for rec in self:
            rec.product_id = rec.request_id.procurement_type_id.product_id