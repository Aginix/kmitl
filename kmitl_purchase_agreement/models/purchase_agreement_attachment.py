# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseAgreementAttachment(models.Model):
    _name = 'purchase.agreement.attachment'
    _description = 'PurchaseAgreementAttachment'

    name = fields.Char('Name')

    request_id = fields.Many2one("agreement", string="Purchase Request")
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")
