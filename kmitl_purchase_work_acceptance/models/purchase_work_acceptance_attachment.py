# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseWorkAcceptanceAttachment(models.Model):
    _name = 'purchase.work.acceptance.attachment'
    _description = 'PurchaseWorkAcceptanceAttachment'

    name = fields.Char('Name')

    request_id = fields.Many2one("agreement", string="Purchase Request")
    file_name = fields.Char(string="Filename")
    file = fields.Binary(string="File", required=True)
    description = fields.Char(string="Description")

