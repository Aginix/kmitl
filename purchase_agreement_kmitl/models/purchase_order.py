# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_create_agreement_from_po(self):
        self.ensure_one()
        agreement = self.env['agreement'].create({
            'name': self.purchase_request_name,
            'contract_type': self.contract_type,
            'assigned_user_id': self.env.user.id,
            'partner_id': self.partner_id.id,
            'purchase_order_id': self.id,
            'company_id': self.company_id.id,
            'expiration_notice': 30,
            'start_date': self.contract_start_date,
            'end_date': self.contract_end_date,
        })

        agreement_lines = []
        for line in self.order_line:
            agreement_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'qty': line.product_qty,
                'uom_id': line.product_uom.id,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
            }))
        agreement.line_ids = agreement_lines

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'agreement',
            'view_mode': 'form',
            'res_id': agreement.id,
            'target': 'current',
        }