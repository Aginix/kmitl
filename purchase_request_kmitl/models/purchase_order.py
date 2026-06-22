# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        tracking=True,
    )
