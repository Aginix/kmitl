# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class TierValidation(models.AbstractModel):
    _inherit = 'tier.validation'

    def _get_tier_validation_readonly_domain(self):
        return []
