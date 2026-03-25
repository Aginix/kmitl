# -*- coding: utf-8 -*-
from odoo import models


class WorkAcceptanceCommittee(models.Model):
    _name = "work.acceptance.committee"
    _inherit = ['work.acceptance.committee', 'portal.mixin', 'mail.thread', 'mail.activity.mixin']

    def get_portal_link(self):
        self.ensure_one()
        self._portal_ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/wa/view/{self.id}?access_token={self.access_token}"
