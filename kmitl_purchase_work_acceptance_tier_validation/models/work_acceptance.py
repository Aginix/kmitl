# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _name = 'work.acceptance'
    _inherit = ['work.acceptance', 'tier.validation']
    _state_from = ["draft"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(WorkAcceptance, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res