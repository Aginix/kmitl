# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    disbursement_request_ids = fields.One2many(
        comodel_name='disbursement.request',
        inverse_name='purchase_id',
        string='Disbursement Requests',
        copy=False,
    )
    disbursement_request_count = fields.Integer(
        string='Disbursement Request Count',
        compute='_compute_disbursement_request',
    )
    disbursement_request_total = fields.Monetary(
        string="Total Disbursement Request",
        compute="_compute_disbursement_request",
        currency_field="currency_id",
        store=False,
    )
    is_disbursement_request_allowed = fields.Boolean(
        string="Can Create Disbursement Request",
        compute="_compute_disbursement_request",
        store=False,
    )
    hide_create_disbursement_request_button = fields.Boolean(
        string="Hide Create Disbursement Request Button",
        compute="_compute_hide_create_disbursement_request_button",
        store=False,
    )

    @api.depends("disbursement_request_ids", "disbursement_request_ids.amount_total")
    def _compute_disbursement_request(self):
        for order in self:
            order.disbursement_request_total = sum(order.disbursement_request_ids.mapped("amount_total"))
            order.is_disbursement_request_allowed = order.disbursement_request_total < order.amount_total
            order.disbursement_request_count = len(order.disbursement_request_ids)

    @api.depends("state", "is_disbursement_request_allowed")
    def _compute_hide_create_disbursement_request_button(self):
        for order in self:
            order.hide_create_disbursement_request_button = (
                order.state != "purchase" or not order.is_disbursement_request_allowed
            )

    def _prepare_disbursement_request_vals(self):
        return {
            "reference": "purchase.order,%d" % self.id,
            "partner_id": self.partner_id.id,
            "line_ids": [
                Command.create(line._prepare_disbursement_request_line_vals())
                for line in self.order_line
            ],
            "ref": self.name,
            "payment_type": self.payment_type,
        }

    def action_disbursement_request(self):
        self.ensure_one()
        disbursement_request = self._create_disbursement_request()
        return {
            "type": "ir.actions.act_window",
            "res_model": "disbursement.request",
            "view_mode": "form",
            "res_id": disbursement_request.id,
            "target": "current",
        }

    def _create_disbursement_request(self):
        disbursement_request = self.env["disbursement.request"].create(
            self._prepare_disbursement_request_vals()
        )
        # Log in PO chatter
        dr_link = "/web#id=%d&model=disbursement.request&view_type=form" % disbursement_request.id
        self.message_post(
            body=_(
                'Disbursement Request <a href="%(link)s" target="_blank">%(name)s</a>'
                " has been created from this purchase order."
            ) % {"link": dr_link, "name": disbursement_request.name},
            subtype_xmlid="mail.mt_note",
        )
        # Log in Disbursement chatter
        po_link = "/web#id=%d&model=purchase.order&view_type=form" % self.id
        disbursement_request.message_post(
            body=_(
                'Created from Purchase Order <a href="%(link)s" target="_blank">%(name)s</a>.'
            ) % {"link": po_link, "name": self.name},
            subtype_xmlid="mail.mt_note",
        )
        self._post_message_to_purchase_requests(disbursement_request)
        return disbursement_request

    def _post_message_to_purchase_requests(self, disbursement_request):
        """Post to related purchase.request(s) if PO was created from PR."""
        if "purchase.request" not in self.env:
            return
        purchase_requests = self.env["purchase.request"]
        for line in self.order_line:
            pr_lines = getattr(line, "purchase_request_lines", None)
            if pr_lines:
                purchase_requests |= pr_lines.mapped("request_id")
        if not purchase_requests:
            return
        dr_link = (
            "/web#id=%d&model=disbursement.request&view_type=form"
            % disbursement_request.id
        )
        for pr in purchase_requests:
            pr.message_post(
                body=_(
                    'Disbursement Request <a href="%(link)s" target="_blank">'
                    "%(name)s</a> has been created from Purchase Order"
                    " %(po_name)s."
                )
                % {
                    "link": dr_link,
                    "name": disbursement_request.name,
                    "po_name": self.name,
                },
                subtype_xmlid="mail.mt_note",
            )

    def action_view_disbursement_request(self):
        self.ensure_one()
        disbursement_requests = self.env['disbursement.request'].search(
            [('purchase_id', '=', self.id)]
        )
        default_reference = "purchase.order,%d" % self.id

        if len(disbursement_requests) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Disbursement Request',
                'res_model': 'disbursement.request',
                'res_id': disbursement_requests.id,
                'view_mode': 'form',
                'context': {'default_reference': default_reference},
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Disbursement Requests',
            'res_model': 'disbursement.request',
            'view_mode': 'tree,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {'default_reference': default_reference},
        }
