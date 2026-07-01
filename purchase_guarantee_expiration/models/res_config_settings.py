# -*- coding: utf-8 -*-
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_guarantee_notify_days = fields.Integer(
        string="Notify Before Guarantee Expiry (Days)",
        default=15,
        config_parameter='purchase_guarantee_expiration.notify_before_days',
    )
