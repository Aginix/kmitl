# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _prepare_agreement_vals(self):
        self.ensure_one()
        return {
            'name': self.purchase_request_name,
            'contract_type': self.contract_type,
            'assigned_user_id': self.env.user.id,
            'partner_id': self.partner_id.id,
            'purchase_order_id': self.id,
            'company_id': self.company_id.id,
            'expiration_notice': 30,
            'start_date': self.contract_start_date,
            'end_date': self.contract_end_date,
        }

    def _prepare_agreement_line_vals(self, line):
        return {
            'product_id': line.product_id.id,
            'name': line.name,
            'qty': line.product_qty,
            'uom_id': line.product_uom.id,
            'price_unit': line.price_unit,
            'price_subtotal': line.price_subtotal,
        }

    def action_create_agreement_from_po(self):
        self.ensure_one()
        agreement_vals = self._prepare_agreement_vals()

        lines = [
            Command.create(self._prepare_agreement_line_vals(line))
            for line in self.order_line
        ]

        agreement_vals['line_ids'] = lines
        agreement = self.env['agreement'].create(agreement_vals)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'agreement',
            'view_mode': 'form',
            'res_id': agreement.id,
            'target': 'current',
        }
