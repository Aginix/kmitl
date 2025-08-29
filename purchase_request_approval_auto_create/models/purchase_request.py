# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "tier.validation"]

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        self._create_approval()

    def _prepare_approval_vals(self):
        vals = super()._prepare_approval_vals()
        vals['operating_unit_id'] = self.operating_unit_id.id
        return vals
