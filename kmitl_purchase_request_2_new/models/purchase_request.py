# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def action_create_pr2(self):
        self.ensure_one()

        pr2 = self.env['purchase.request.two'].create({
            'pr1_ref': self.id,
            'purchase_request_number': self.name,
            'payment_type': self.payment_type,
        })

        line_vals = []
        for line in self.line_ids:
            line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'description': line.name,
                'quantity': line.product_qty,
            }))
        pr2.write({'line_ids': line_vals})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.two',
            'view_mode': 'form',
            'res_id': pr2.id,
            'target': 'current',
        }