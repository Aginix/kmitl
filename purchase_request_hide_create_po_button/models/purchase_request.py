# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    hide_create_po_button = fields.Boolean(compute="_hide_create_po_button")

    @api.depends('state')
    def _hide_create_po_button(self):
        for rec in self:
            rec.hide_create_po_button = True
            if rec.state in ('approved', 'in_progress') and rec.purchase_count == 0:
                rec.hide_create_po_button = False
