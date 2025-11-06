# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class TierValidation(models.AbstractModel):
    _inherit = 'tier.validation'

    has_approve_comment = fields.Boolean(compute="_compute_has_approve_comment")
    has_reject_comment = fields.Boolean(compute="_compute_has_reject_comment")

    def _compute_has_approve_comment(self):
        for rec in self:
            has_approve_comment = rec.review_ids.filtered(
                lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
            ).mapped("has_approve_comment")
            rec.has_approve_comment = True in has_approve_comment

    def _compute_has_reject_comment(self):
        for rec in self:
            has_reject_comment = rec.review_ids.filtered(
                lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
            ).mapped("has_reject_comment")
            rec.has_reject_comment = True in has_reject_comment

    def validate_tier(self):
        """Extended version — safe for future inheritance"""
        self.ensure_one()
        sequences = self._get_sequences_to_approve(self.env.user)
        reviews = self.review_ids.filtered(
            lambda l: l.sequence in sequences or l.approve_sequence_bypass
        )

        has_comment = getattr(self, "has_comment", False)
        has_approve_comment = getattr(self, "has_approve_comment", False)
        # original has no "self.has_approve_comment"
        if has_comment and has_approve_comment:
            user_reviews = reviews.filtered(
                lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
            )
            return self._add_comment("validate", user_reviews)

        res = super().validate_tier()
        self._update_counter({"review_deleted": True})

        return res

    def reject_tier(self):
        self.ensure_one()
        sequences = self._get_sequences_to_approve(self.env.user)
        reviews = self.review_ids.filtered(lambda l: l.sequence in sequences)
        # original has no "self.has_reject_comment"
        if self.has_comment and self.has_reject_comment:
            return self._add_comment("reject", reviews)
        self._rejected_tier(reviews)
        self._update_counter({"review_deleted": True})
