# -*- coding: utf-8 -*-
from odoo import _, models

WA_REVIEW_ACTIVITY = (
    "purchase_work_acceptance_todo.mail_activity_wa_review_requested"
)


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    def _notify_review_requested(self, tier_reviews):
        """Schedule a Todo per reviewer instead of OCA's subscribe/message_post
        so the reviewer sees a single unified entry in the mail_activity_todo
        systray. Execution category → cleared by Accept/Reject on the source."""
        act_type = self.env.ref(WA_REVIEW_ACTIVITY, raise_if_not_found=False)
        if not act_type:
            return
        for rec in self.sudo():
            reviewers = tier_reviews.filtered(
                lambda r: r.res_id == rec.id
            ).mapped("reviewer_ids")
            for user in reviewers:
                rec.activity_schedule(
                    WA_REVIEW_ACTIVITY,
                    summary=_("Work acceptance %s awaits your review") % rec.name,
                    user_id=user.id,
                )

    def _validate_tier(self, reviews):
        res = super()._validate_tier(reviews)
        self.activity_feedback([WA_REVIEW_ACTIVITY], user_id=self.env.uid)
        return res

    def _rejected_tier(self, tiers=False):
        res = super()._rejected_tier(tiers=tiers)
        self.activity_feedback([WA_REVIEW_ACTIVITY], user_id=self.env.uid)
        return res

    def write(self, vals):
        clear_ids = []
        if vals.get("state") and vals["state"] != "in_review":
            clear_ids = [rec.id for rec in self if rec.state == "in_review"]
        res = super().write(vals)
        if clear_ids:
            act_type = self.env.ref(WA_REVIEW_ACTIVITY, raise_if_not_found=False)
            if act_type:
                self.env["mail.activity"].sudo().search([
                    ("res_model", "=", "work.acceptance"),
                    ("res_id", "in", clear_ids),
                    ("activity_type_id", "=", act_type.id),
                ]).unlink()
        return res
