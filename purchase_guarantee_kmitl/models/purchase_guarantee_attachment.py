# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuaranteeAttachment(models.Model):
    _name = 'purchase.guarantee.attachment'
    _description = 'PurchaseGuaranteeAttachment'

    name = fields.Char('Name')

    request_id = fields.Many2one("purchase.guarantee", string="Purchase Guarantee")
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")