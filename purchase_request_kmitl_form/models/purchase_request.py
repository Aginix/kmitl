# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def button_create_pr2(self):
        self.ensure_one()
        ref_code = self.env['ir.sequence'].next_by_code('purchase.request.form')
        line_vals = []
        for line in self.line_ids:
            line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'description': line.name,
                'quantity': line.product_qty,
            }))
        form = self.env['purchase.request.form'].create({
            'ref': ref_code,
            'purchase_request_id': self.id,
            'line_ids':line_vals,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('PR2 Form'),
            'res_model': 'purchase.request.form',
            'view_mode': 'form',
            'res_id': form.id,
            'target': 'current',
        }
