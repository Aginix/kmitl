# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrderAttachment(models.Model):
    _name = 'purchase.order.attachment'
    _description = 'PurchaseOrderAttachment'

    request_id = fields.Many2one("purchase.order", string="Purchase Request")
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")
