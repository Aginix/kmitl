from lxml import etree

from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "tier.validation"]
    _state_from = ["validation"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    is_purchase_request = fields.Boolean(compute="_compute_is_purchase_request")

    def _compute_is_purchase_request(self):
        for rec in self:
            rec.is_purchase_request = rec._name == "purchase.request"

    def _validate_tier(self, tiers=False):
        super(PurchaseRequest, self)._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.write({'state': 'approved', 'approved_by': self.env.user.id, 'date_approved': fields.Date.context_today(self)})

    @api.model
    def _get_under_validation_exceptions(self):
        exceptions = super()._get_under_validation_exceptions()
        exceptions.append('validated_field')
        return exceptions

    def button_draft(self):
        self.restart_validation()
        return super().button_draft()

    def button_tier_to_approve(self):
        return super().button_to_approve()

    def _add_tier_validation_buttons(self, node, params):
        if self.is_purchase_request:
            str_element = self.env["ir.qweb"]._render(
                "base_tier_validation.tier_validation_buttons", params
            )
            new_node = etree.fromstring(str_element)
            return new_node
        return etree.Element("div")
