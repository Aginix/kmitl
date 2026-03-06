# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_contract_notify_days = fields.Integer(
        string="Notify Before Contract Expiry (Days)",
        default=15,
        config_parameter='purchase_order_notification.notify_before_days',
    )
