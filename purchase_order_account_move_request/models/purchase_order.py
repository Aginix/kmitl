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
        compute='_compute_move_request',
    )
    move_request_total = fields.Monetary(
        string="Total Move Request",
        compute="_compute_move_request",
        currency_field="currency_id",
        store=False,
    )
    is_move_request_allowed = fields.Boolean(
        string="Can Create Move Request",
        compute="_compute_move_request",
        store=False,
    )
    hide_create_move_request_button = fields.Boolean(
        string="Hide Create Move Request Button",
        compute="_compute_hide_create_move_request_button",
        store=False,
    )

    @api.depends("move_request_ids", "move_request_ids.amount_total")
    def _compute_move_request(self):
        for order in self:
            order.move_request_total = sum(order.move_request_ids.mapped("amount_total"))
            order.is_move_request_allowed = order.move_request_total < order.amount_total
            order.move_request_count = len(order.move_request_ids)

    @api.depends("state", "is_move_request_allowed")
    def _compute_hide_create_move_request_button(self):
        for order in self:
            order.hide_create_move_request_button = (
                order.state != "purchase" or not order.is_move_request_allowed
            )

    def _prepare_move_request_vals(self):
        return {
            "purchase_id": self.id,
            "partner_id": self.partner_id.id,
            "line_ids": [
                Command.create(line._prepare_move_request_line_vals())
                for line in self.order_line
            ],
            "ref": self.name,
            "payment_type": self.payment_type,
        }

    def action_move_request(self):
        self.ensure_one()
        move_request = self._create_move_request()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.request",
            "view_mode": "form",
            "res_id": move_request.id,
            "target": "current",
        }

    def _create_move_request(self):
        move_request = self.env["account.move.request"].create(
            self._prepare_move_request_vals()
        )
        return move_request

    def action_view_move_request(self):
        self.ensure_one()
        move_requests = self.env['account.move.request'].search(
            [('purchase_id', '=', self.id)]
        )
        
        if len(move_requests) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Move Request',
                'res_model': 'account.move.request',
                'res_id': move_requests.id,
                'view_mode': 'form',
                'context': {'default_purchase_id': self.id},
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Move Requests',
            'res_model': 'account.move.request',
            'view_mode': 'tree,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {'default_purchase_id': self.id},
        }
