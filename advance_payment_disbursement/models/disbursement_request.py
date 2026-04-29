# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DisbursementRequest(models.Model):
    _inherit = 'disbursement.request'

    advance_payment_id = fields.Many2one(
        'advance.payment',
        string='Advance Payment',
    )
