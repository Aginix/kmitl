# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    request_id = fields.Many2one(
        "purchase.request",
        compute="_compute_request_id",
        string="Purchase Request",
    )

    @api.depends("purchase_request_lines")
    def _compute_request_id(self):
        for rec in self:
            for request_line in rec.order_line.mapped('purchase_request_lines'):
                rec.request_id = request_line.request_id.id
                break
