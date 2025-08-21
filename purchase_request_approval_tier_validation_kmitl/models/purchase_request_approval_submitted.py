from lxml import etree

from odoo import _, api, fields, models


class PurchaseRequestApprovalSubmitted(models.Model):
    _name = 'purchase.request.approval.submitted'
    _inherit = ['purchase.request.approval.submitted', 'tier.validation']
    _state_from = ["draft"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    is_purchase_request_approval = fields.Boolean(compute="_compute_is_purchase_request_approval")

    def _compute_is_purchase_request_approval(self):
        for rec in self:
            rec.is_purchase_request_approval = rec._name == "purchase.request.approval.submitted"

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(PurchaseRequestApprovalSubmitted, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res

    def _validate_tier(self, tiers=False):
        super(PurchaseRequestApprovalSubmitted, self)._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            for line in self.line_ids:
                line.pr2_form_id.state = 'approved'
            return self.write({'state': 'approved', 'approved_by': self.env.user.id, 'approved_date': fields.Date.context_today(self)})

    def _add_tier_validation_buttons(self, node, params):
        if self.is_purchase_request_approval:
            str_element = self.env["ir.qweb"]._render(
                "base_tier_validation.tier_validation_buttons", params
            )
            new_node = etree.fromstring(str_element)
            return new_node
        return etree.Element("div")
