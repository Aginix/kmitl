# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptanceLine(models.Model):
    _inherit = 'work.acceptance.line'

    percent_qty_accepted = fields.Float(
        string="Percent",
        related="wa_id.installment_id.percent",
    )