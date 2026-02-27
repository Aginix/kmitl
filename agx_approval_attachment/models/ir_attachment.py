# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    attachment_type = fields.Selection(
        [
            ("tor", "Specification (TOR)"),
            ("rfq", "Quotation"), 
            ("etc", "Etc"),
        ],
        string="Attachment Type"
    )
    sequence = fields.Integer(string="Sequence")