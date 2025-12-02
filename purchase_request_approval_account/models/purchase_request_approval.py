# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    use_purchase_order = fields.Boolean(
        string='Use Purchase Order',
        default=True,
        tracking=True
    )

    account_move_request_ids = fields.One2many(
        comodel_name="account.move.request",
        inverse_name="purchase_request_approval_id",
        string='Move Requests',
    )

    billing_status = fields.Selection(
        selection=[('nothing', 'Nothing'), ('', '')],
        string='Billing Status',
        compute="_compute_billing_status",
        store=True,
        tracking=True,
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

    @api.depends("account_move_request_ids", "account_move_request_ids.amount_total")
    def _compute_move_request(self):
        for approval in self:
            approval.move_request_total = sum(approval.account_move_request_ids.mapped("amount_total"))
            # approval.is_move_request_allowed = approval.move_request_total < approval.amount_total
            approval.move_request_count = len(approval.account_move_request_ids)

    @api.depends("account_move_request_ids", "account_move_request_ids.state")
    def _compute_billing_status(self):
        print("test")

    def _create_account_move_request(self):
        print("create")
