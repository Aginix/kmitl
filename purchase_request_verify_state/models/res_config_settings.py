# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_request_allow_verify_state = fields.Boolean(
        string='Activate verification step for procurement officer',
        config_parameter='purchase_request_verification.enable_verification',
        help="Add a verification step for procurement officers before proceeding to the payment stage",
    )
