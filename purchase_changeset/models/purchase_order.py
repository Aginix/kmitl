# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_committee_ids = fields.One2many(
        comodel_name="purchase.committee",
        inverse_name="purchase_id",
        string="Purchase Committees",
        copy=True,
    )
