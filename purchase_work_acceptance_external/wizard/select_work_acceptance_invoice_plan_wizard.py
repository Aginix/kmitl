# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SelectWorkAcceptanceInvoicePlanWizard(models.TransientModel):
    _inherit = 'select.work.acceptance.invoice.plan.wizard'

    is_external = fields.Boolean(
        string='Use External Inspection',
        default=False,
    )

    @api.onchange('order_id')
    def _onchange_order_id_external(self):
        if self.order_id:
            self.is_external = self.order_id.is_external

    @api.model
    def default_get(self, field_list):
        res = super().default_get(field_list)
        order = self.env['purchase.order'].browse(
            self.env.context.get('active_id')
        )
        if order:
            res['is_external'] = order.is_external
        return res

    def button_create_wa(self):
        res = super().button_create_wa()
        res['context']['default_is_external'] = self.is_external
        return res