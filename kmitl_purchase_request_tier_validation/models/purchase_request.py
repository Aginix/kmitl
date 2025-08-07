from odoo import _, api, fields, models


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

    def _validate_tier(self, tiers=False):
        super(PurchaseRequest, self)._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.write({'state': 'approved', 'approved_by': self.env.user.id, 'date_approved': fields.Date.context_today(self)})
