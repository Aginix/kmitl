# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    show_create_incoming_button = fields.Boolean(
        string="Can Show Incoming Shipment Button",
        compute="_compute_show_create_incoming_button",
        store=False
    )

    @api.depends('use_invoice_plan', 'wa_accepted', 'invoice_plan_ids', 'invoice_plan_ids.installment')
    def _compute_show_create_incoming_button(self):
        for order in self:
            if order.use_invoice_plan:
                accepted_wa = self.env['work.acceptance'].search([
                    ('installment_id.purchase_id', '=', order.id),
                    ('state', '=', 'accept')
                ], limit=1)
                order.show_create_incoming_button = bool(accepted_wa)
            else:
                order.show_create_incoming_button = order.wa_accepted
