# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    team_id = fields.Many2one(
        'purchase.team',
        string='Purchase Team',
        tracking=True,
        index=True,
        domain="[('assign_on_po', '=', True)]",
        help='Purchase team responsible for this request'
    )
    
