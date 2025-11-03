# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    move_request_ids = fields.One2many(
        comodel_name='account.move.request',
        inverse_name='purchase_id',
        string='Move Requests',
    )
    move_reaquest_count = fields.Integer(
        string='Move Request Count',
        compute='_compute_move_request_count',
    )
    @api.depends('move_request_ids')
    def _compute_move_request_count(self):
        for order in self:
            order.move_reaquest_count = len(order.move_request_ids)

    def action_move_request(self):
        self.ensure_one()

        line_vals = []
        for line in self.order_line:
            account = (
                line.product_id.property_account_expense_id
                or line.product_id.categ_id.property_account_expense_categ_id
            )
            if account:
                line.account_id = account
            line_vals.append(
                Command.create(
                    {
                        "product_id": line.product_id.id,
                        "name": line.name,
                        "quantity": line.product_qty,
                        "price_unit": line.price_unit,
                        "account_id": line.account_id.id,
                        "tax_ids": [Command.set(line.taxes_id.ids)],
                        "analytic_distribution": line.analytic_distribution,
                    }
                )
            )

        move_request = self.env['account.move.request'].create({
            'purchase_id': self.id,
            'partner_id': self.partner_id.id,
            'line_ids': line_vals,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.request',
            'view_mode': 'form',
            'res_id': move_request.id,
            'target': 'current',
        }

    def action_view_move_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Move Requests',
            'res_model': 'account.move.request',
            'view_mode': 'tree,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {'default_purchase_id': self.id},
        }
