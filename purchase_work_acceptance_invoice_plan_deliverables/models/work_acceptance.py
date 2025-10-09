# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    deliverables=fields.Text(
        string='Deliverables',
        related='installment_id.deliverables',
        readonly=True,
        store=False
    )