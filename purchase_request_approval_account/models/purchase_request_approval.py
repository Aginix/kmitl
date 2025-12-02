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
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("validated", "Validated"),
            ("cancel", "Cancelled"),
        ],
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

    purchase_count = fields.Integer(
        related="request_id.purchase_count",
        store=True,
    )

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(self.id, self._name)

    def approval_make_purchase_order(self):
        return self.request_id.approval_make_purchase_order()

    def action_view_purchase_order(self):
        return self.request_id.action_view_purchase_order()

    @api.depends("account_move_request_ids", "account_move_request_ids.amount_total")
    def _compute_move_request(self):
        for approval in self:
            approval.move_request_total = sum(approval.account_move_request_ids.mapped("amount_total"))
            approval.move_request_count = len(approval.account_move_request_ids)

    @api.depends("account_move_request_ids", "account_move_request_ids.state")
    def _compute_billing_status(self):
        for approval in self:
            approval.billing_status = approval.account_move_request_ids.state

    def _prepare_move_request_vals(self):
        return {
            "purchase_request_approval_id": self.id,
            "partner_id": self.request_id.partner_id.id,
            "line_ids": [
                Command.create(line._prepare_move_request_line_vals())
                for line in self.request_id.line_ids
            ],
            "ref": self.request_id.name,
            "payment_type": self.request_id.payment_type,
        }

    def action_view_move_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.request",
            "view_mode": "form,tree",
            "res_id": self.account_move_request_ids.id,
            "target": "current",
        }

    def action_move_request(self):
        self.ensure_one()
        move_request = self._create_account_move_request()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move.request",
            "view_mode": "form",
            "res_id": move_request.id,
            "target": "current",
        }

    def _create_account_move_request(self):
        move_request = self.env["account.move.request"].create(
            self._prepare_move_request_vals()
        )
        link_back_message = move_request._message_link_back_to_request()
        move_request.message_post(body=link_back_message, message_type="comment")
        message = self._purchase_request_approval_create_bill_message_content(move_request)
        self.message_post(body=message, message_type="comment")
        return move_request

    def _purchase_request_approval_create_bill_message_content(self, move_request):
        message = _(
            "Billing %(mr_name)s for %(pa_name)s created successfully, waiting for operation."
        ) % {
            "mr_name": move_request.name,
            "pa_name": self.name,
        }

        return message
