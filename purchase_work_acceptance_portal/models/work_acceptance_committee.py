# -*- coding: utf-8 -*-
from odoo import api, models

WA_REVIEW_ACT_TYPE_XMLID = (
    "purchase_work_acceptance_portal.mail_activity_type_wa_review"
)


class WorkAcceptanceCommittee(models.Model):
    _name = "work.acceptance.committee"
    _inherit = ['work.acceptance.committee', 'portal.mixin', 'mail.thread', 'mail.activity.mixin']

    def get_portal_link(self):
        self.ensure_one()
        self._portal_ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/wa/view/{self.id}?access_token={self.access_token}"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Adding a committee while the WA is already under review must hand
        # them a Todo immediately — request_validation has already run.
        for c in records:
            if c.wa_id.state == "in_review":
                c.wa_id._schedule_committee_review_activities()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get("status"):
            # A truthy status means the committee acted — close the Todo and
            # log the decision. button_draft() clears status back to "" which
            # is falsy, so it does NOT trip this branch (cancellation is
            # handled by _cancel_review_activities on the WA).
            self._feedback_review_activities()
        return res

    def unlink(self):
        self._unlink_pending_review_activities()
        return super().unlink()

    def _feedback_review_activities(self):
        act_type = self.env.ref(
            WA_REVIEW_ACT_TYPE_XMLID, raise_if_not_found=False
        )
        if not act_type:
            return
        Activity = self.env["mail.activity"].sudo()
        status_labels = dict(self._fields["status"].selection)
        for c in self:
            user = c.employee_id.user_id
            if not user:
                continue
            activities = Activity.search([
                ("res_model", "=", "work.acceptance"),
                ("res_id", "=", c.wa_id.id),
                ("user_id", "=", user.id),
                ("activity_type_id", "=", act_type.id),
            ])
            if not activities:
                continue
            feedback = c.note or status_labels.get(c.status) or c.status
            activities.action_feedback(feedback=feedback)

    def _unlink_pending_review_activities(self):
        act_type = self.env.ref(
            WA_REVIEW_ACT_TYPE_XMLID, raise_if_not_found=False
        )
        if not act_type:
            return
        Activity = self.env["mail.activity"].sudo()
        for c in self:
            user = c.employee_id.user_id
            if not user:
                continue
            Activity.search([
                ("res_model", "=", "work.acceptance"),
                ("res_id", "=", c.wa_id.id),
                ("user_id", "=", user.id),
                ("activity_type_id", "=", act_type.id),
            ]).unlink()
