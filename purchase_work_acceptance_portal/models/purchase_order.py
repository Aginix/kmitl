# -*- coding: utf-8 -*-
from odoo import models


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = ['purchase.order', 'portal.mixin']

    def get_portal_link(self):
        self.ensure_one()
        # Portal is the whole point — sudo the ensure_token so callers
        # gated by operating-unit rules can still be handed a valid URL.
        self.sudo()._portal_ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/purchase/view/{self.id}?access_token={self.access_token}"
