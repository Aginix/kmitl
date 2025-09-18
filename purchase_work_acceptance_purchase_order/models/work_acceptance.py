# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    def action_view_purchase_order(self):
        self.ensure_one()
        if not self.purchase_id:
            return
            
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': self.env.context,
        }