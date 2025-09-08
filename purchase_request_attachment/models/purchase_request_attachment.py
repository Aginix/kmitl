# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestAttachment(models.Model):
    _name = 'purchase.request.attachment'
    _description = 'PurchaseRequestAttachment'

    request_id = fields.Many2one("purchase.request", string="Purchase Request")
    attachment_type = fields.Selection(
        [
            ("tor", "Specification (TOR)"),
            ("rfq", "Quotation"),
            ("etc", "Etc"),
        ],
    )
    attachment_id = fields.Binary(string="Upload File", attachment=True)
    file_name = fields.Char(string="Filename")
    description = fields.Char(string="Description")