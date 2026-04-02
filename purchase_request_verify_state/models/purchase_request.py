# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    state = fields.Selection(
        selection_add = [('to_examine', 'To Examine'), ('to_verify',)],
        ondelete={'to_examine': 'set default'},
        
    )

    def _is_verification_enabled(self):
        return (
            self.env['ir.config_parameter']
            .sudo()
            .get_param('purchase_request_verification.enable_verification', default=False)
            == 'True'
        )

    def button_to_verify(self):
        if self._is_verification_enabled():
            to_examine = self.filtered(lambda r: r.state == 'draft')
            super().button_to_verify()
            to_examine.write({'state': 'to_examine'})
            return True
        return super().button_to_verify()
    
    def button_examine(self):
        return self.write({"state": "to_verify"})
