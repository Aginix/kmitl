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

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)

        for rec in self:
            reviews = rec.review_ids.filtered(
                lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
            )
            if not reviews:
                rec.write({'state': 'done', 'approval_date': fields.Datetime.now()})

                if rec.request_ids:
                    rec.request_ids._write({'state': 'approved'})

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("state")
        return res
