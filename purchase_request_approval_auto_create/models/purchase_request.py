# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "tier.validation"]

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        approval = self.env['purchase.request.approval'].create({
            'request_id': self.id,
            'purchase_request_number': self.name,
        })

        line_vals = []
        for line in self.line_ids:
            line_vals.append(Command.create({
                'product_id': line.product_id.id,
                'description': line.name,
                'product_qty': line.product_qty,
                'price_unit': line.estimated_cost / line.product_qty if line.product_qty else 0,
            }))
        self.write({'approval_id': approval.id})
        approval.write({'line_ids': line_vals})
