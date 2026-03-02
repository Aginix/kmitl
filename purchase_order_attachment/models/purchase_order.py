# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string='Document Attachments',
        tracking=True,
    )