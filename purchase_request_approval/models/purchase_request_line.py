# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    def _prepare_approval_line_vals(self):
        return {
            'product_id': line.product_id.id,
            'description': line.name,
            'product_qty': line.product_qty,
            'price_unit': line.estimated_cost / line.product_qty if line.product_qty else 0,
        }
