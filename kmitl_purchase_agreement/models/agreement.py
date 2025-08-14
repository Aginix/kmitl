# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Agreement(models.Model):
    _inherit = 'agreement'

    document_ids = fields.One2many(
        "purchase.agreement.attachment",
        "request_id",
        string="Attachment",
    )

    purchase_order_id = fields.Many2one(
        'purchase.order', string="Purchase Order", ondelete="set null"
    )