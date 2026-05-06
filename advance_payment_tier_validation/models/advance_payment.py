from lxml import etree

from odoo import api, fields, models


class AdvancePayment(models.Model):
    _name = "advance.payment"
    _inherit = ["advance.payment", "tier.validation"]
    _state_from = ["submitted"]
    _state_to = ["approved"]
    _tier_validation_manual_config = False

    state = fields.Selection(
        selection_add=[("rejected", "ไม่อนุมัติ")],
        ondelete={"rejected": "set default"},
    )

    def _add_tier_validation_buttons(self, node, params):
        return etree.Element("div")

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("return_line_ids")
        return res

    @api.model
    def _get_all_validation_exceptions(self):
        res = super()._get_all_validation_exceptions()
        res.append("return_line_ids")
        return res

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        res.append("return_line_ids")
        return res

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.action_approve()

    def _rejected_tier(self, tiers=False):
        super()._rejected_tier(tiers=tiers)
        for rec in self:
            if rec.state == "submitted":
                rec.state = "rejected"
                rec._propagate_rejection_to_reference()

    def _propagate_rejection_to_reference(self):
        self.ensure_one()
        ref = self.reference
        if not ref or ref._name != "purchase.request":
            return
        pr = self.env["purchase.request"].browse(ref.id)
        if pr.exists() and pr.state != "rejected":
            pr.button_rejected()
