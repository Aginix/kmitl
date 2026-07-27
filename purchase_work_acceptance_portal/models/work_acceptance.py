# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

WA_REVIEW_ACTIVITY = (
    "purchase_work_acceptance_portal.mail_activity_wa_review_requested"
)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    is_current_user_committee = fields.Boolean(
        compute="_compute_is_current_user_committee",
        compute_sudo=True,
        help="True when the current user is on this WA's committee. "
        "Non-stored, re-evaluated per viewer.",
    )

    @api.depends("work_acceptance_committee_ids.employee_id.user_id")
    @api.depends_context("uid")
    def _compute_is_current_user_committee(self):
        uid = self.env.uid
        for rec in self:
            rec.is_current_user_committee = any(
                c.employee_id.user_id.id == uid
                for c in rec.work_acceptance_committee_ids
            )

    def get_portal_link(self):
        self.ensure_one()
        self._portal_ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/wa/view/{self.id}?access_token={self.access_token}"

    def action_open_committee_portal(self):
        self.ensure_one()
        committee = self.sudo().work_acceptance_committee_ids.filtered(
            lambda c: c.employee_id.user_id.id == self.env.uid
        )[:1]
        committee._portal_ensure_token()
        return {
            "type": "ir.actions.act_url",
            "url": f"{self.get_portal_link()}&committee_token={committee.access_token}",
            "target": "new",
        }

    def action_open_purchase_portal(self):
        self.ensure_one()
        po_url = self.purchase_id.sudo().get_portal_link()
        self._portal_ensure_token()
        return {
            "type": "ir.actions.act_url",
            "url": f"{po_url}&wa_token={self.access_token}",
            "target": "new",
        }

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
