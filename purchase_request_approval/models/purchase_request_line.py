# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    def _prepare_approval_line_vals(self):
        return {
            'product_id': self.product_id.id,
            'description': self.name,
            'product_qty': self.product_qty,
            'price_unit': self.estimated_cost / self.product_qty if self.product_qty else 0,
        }
