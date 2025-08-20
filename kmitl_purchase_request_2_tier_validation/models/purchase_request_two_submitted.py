from lxml import etree

from odoo import _, api, fields, models


class PurchaseRequestTwoSubmitted(models.Model):
    _name = 'purchase.request.two.submitted'
    _inherit = ['purchase.request.two.submitted', 'tier.validation']
    _state_from = ["draft"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    is_purchase_request = fields.Boolean(compute="_compute_is_purchase_request")

    def _compute_is_purchase_request(self):
        for rec in self:
            rec.is_purchase_request = rec._name == "purchase.request.two.submitted"

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseRequestTwoSubmitted, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res

    def _validate_tier(self, tiers=False):
        super(PurchaseRequestTwoSubmitted, self)._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            for line in self.line_ids:
                line.pr2_form_id.state = 'approved'
            return self.write({'state': 'approved', 'approval_by': self.env.user.id, 'approval_date': fields.Date.context_today(self)})

    def _add_tier_validation_buttons(self, node, params):
        if self.is_purchase_request:
            str_element = self.env["ir.qweb"]._render(
                "base_tier_validation.tier_validation_buttons", params
            )
            new_node = etree.fromstring(str_element)
            return new_node
        return etree.Element("div")
