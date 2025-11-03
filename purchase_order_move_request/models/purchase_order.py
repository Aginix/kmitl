# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    move_request_ids = fields.One2many(
        comodel_name='account.move.request',
        inverse_name='purchase_id',
        string='Move Requests',
    )
    move_request_count = fields.Integer(
        string='Move Request Count',
        compute='_compute_move_request_count',
    )

    @api.depends('move_request_ids')
    def _compute_move_request_count(self):
        for order in self:
            order.move_request_count = len(order.move_request_ids)

    def _prepare_move_request_line_vals(self, line):
        account = (
            line.product_id.property_account_expense_id
            or line.product_id.categ_id.property_account_expense_categ_id
        )
        return {
            "product_id": line.product_id.id,
            "name": line.name,
            "quantity": line.product_qty,
            "price_unit": line.price_unit,
            "account_id": account.id if account else False,
            "tax_ids": [Command.set(line.taxes_id.ids)],
            "analytic_distribution": line.analytic_distribution,
        }

    def _prepare_move_request_vals(self):
        return {
            "purchase_id": self.id,
            "partner_id": self.partner_id.id,
            "line_ids": [
                Command.create(self._prepare_move_request_line_vals(line))
                for line in self.order_line
            ],
        }

    def action_move_request(self):
        self.ensure_one()
        move_request = self.env["account.move.request"].create(
            self._prepare_move_request_vals()
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.request",
            "view_mode": "form",
            "res_id": move_request.id,
            "target": "current",
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
