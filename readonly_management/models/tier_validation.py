# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TierValidation(models.AbstractModel):
    _inherit = 'tier.validation'

    def _get_tier_validation_readonly_domain(self):
        return []
