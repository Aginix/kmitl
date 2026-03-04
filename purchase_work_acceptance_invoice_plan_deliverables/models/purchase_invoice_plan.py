# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseInvoicePlan(models.Model):
    _inherit = 'purchase.invoice.plan'

    deliverables=fields.Text(
        string='Deliverables'
    )