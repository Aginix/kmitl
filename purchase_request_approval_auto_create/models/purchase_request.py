# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "tier.validation"]

    def _prepare_approval_vals(self):
        return {
            'request_id': self.id,
            'purchase_request_number': self.name,
            'line_ids': [Command.create(line._prepare_approval_line_vals()) for line in self.line_ids],
        }

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        self._create_approval()

    def _create_approval(self):
        approval = self.env['purchase.request.approval'].create(self._prepare_approval_vals())
        self.write({'approval_id': approval.id})

