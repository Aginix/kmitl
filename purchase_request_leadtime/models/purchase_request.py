# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = ['purchase.request', 'state.leadtime.mixin']

    _tracked_transitions = [
        ('to_approve', 'approved'),
    ]