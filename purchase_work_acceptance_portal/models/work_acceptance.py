# -*- coding: utf-8 -*-
from odoo import _, models

WA_REVIEW_ACTIVITY = (
    "purchase_work_acceptance_portal.mail_activity_wa_review_requested"
)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    def get_portal_link(self):
        self.ensure_one()
        self._portal_ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/wa/view/{self.id}?access_token={self.access_token}"

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

    def _notify_accepted_reviews(self):
        res = super()._notify_accepted_reviews()
        self.activity_feedback([WA_REVIEW_ACTIVITY], user_id=self.env.uid)
        return res

    def _notify_rejected_review(self):
        res = super()._notify_rejected_review()
        self.activity_feedback([WA_REVIEW_ACTIVITY], user_id=self.env.uid)
        return res
