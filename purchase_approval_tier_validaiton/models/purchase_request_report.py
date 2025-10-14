# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestReport(models.Model):
    _name = 'purchase.request.report'
    _inherit = ["purchase.request.report", "tier.validation"]
    _state_from = ["submit"]
    _state_to = ["done"]

    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseRequestReport, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res
