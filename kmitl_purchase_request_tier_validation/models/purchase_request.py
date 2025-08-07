# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "tier.validation"]
    _state_from = ["validation"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseRequest, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res

    @api.onchange('review_ids')
    def _onchange_validation_status(self):
        if self.validreview_idsated == False:
            self.state = 'approved'

