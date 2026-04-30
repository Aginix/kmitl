from odoo import api, models


class AdvancePayment(models.Model):
    _name = "advance.payment"
    _inherit = ["advance.payment", "tier.validation"]
    _state_from = ["submitted"]
    _state_to = ["approved"]
    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("return_line_ids")
        return res

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.action_approve()
