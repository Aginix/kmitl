# -*- coding: utf-8 -*-
from odoo import api, models


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def configurator_init(self):
        result = super().configurator_init()
        # Ensure 'industries' is always a list even when the IAP API is
        # unreachable (no internet) — prevents JS `.map()` crash in the
        # website setup wizard.
        result.setdefault('industries', [])
        return result
