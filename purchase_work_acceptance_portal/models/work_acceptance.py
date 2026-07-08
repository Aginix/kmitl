# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

WA_REVIEW_ACT_TYPE_XMLID = (
    "purchase_work_acceptance_portal.mail_activity_type_wa_review"
)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    is_current_user_committee = fields.Boolean(
        compute="_compute_is_current_user_committee",
        help="Technical: env.user is one of the committee members on this WA. "
        "Drives visibility of the portal smart button.",
    )

    @api.depends("work_acceptance_committee_ids.employee_id.user_id")
    @api.depends_context("uid")
    def _compute_is_current_user_committee(self):
        uid = self.env.uid
        for wa in self:
            wa.is_current_user_committee = uid in wa.work_acceptance_committee_ids.mapped(
                "employee_id.user_id.id"
            )

    def get_portal_link(self):
        self.ensure_one()
        self._portal_ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/wa/view/{self.id}?access_token={self.access_token}"

    def action_open_committee_portal(self):
        """Smart button: open the WA portal page in a new tab, carrying the
        current user's own ``committee_token`` so accept/reject controls
        resolve against the right committee row.
        """
        self.ensure_one()
        committee = self.work_acceptance_committee_ids.filtered(
            lambda c: c.employee_id.user_id == self.env.user
        )[:1]
        if not committee:
            raise UserError(_(
                "You are not a committee member of this Work Acceptance."
            ))
        return {
            "type": "ir.actions.act_url",
            "url": "%s&committee_token=%s" % (
                self.get_portal_link(), committee.access_token,
            ),
            "target": "new",
        }

    def action_open_purchase_portal(self):
        """Smart button: open the linked PO portal page, gated by the WA's
        own ``access_token`` re-used as ``wa_token``.
        """
        self.ensure_one()
        if not self.purchase_id:
            raise UserError(_(
                "This Work Acceptance has no linked Purchase Order."
            ))
        self._portal_ensure_token()
        return {
            "type": "ir.actions.act_url",
            "url": "%s&wa_token=%s" % (
                self.purchase_id.get_portal_link(), self.access_token,
            ),
            "target": "new",
        }

    def _notify_review_requested(self, tier_reviews):
        """Suppress tier validation mail notifications — committee review
        is surfaced through mail_activity_todo instead.
        """
        return

    def request_validation(self):
        for wa in self:
            missing = wa.work_acceptance_committee_ids.filtered(
                lambda c: not c.employee_id.user_id
            )
            if missing:
                names = ", ".join(missing.mapped("name"))
                raise UserError(_(
                    "Committee members must have a linked user "
                    "to receive review Todos: %s"
                ) % names)
        res = super().request_validation()
        for wa in self:
            wa._schedule_committee_review_activities()
        return res

    def button_draft(self):
        # Returning to draft means no committee decision will land — drop
        # the pending review Todos without writing them to todo.log.
        self._cancel_review_activities()
        return super().button_draft()

    def _schedule_committee_review_activities(self):
        """Create one Approval Todo per committee user; idempotent."""
        self.ensure_one()
        act_type = self.env.ref(WA_REVIEW_ACT_TYPE_XMLID)
        Activity = self.env["mail.activity"].sudo()
        for committee in self.work_acceptance_committee_ids:
            user = committee.employee_id.user_id
            if not user:
                continue  # validated up-front in request_validation()
            existing = Activity.search([
                ("res_model", "=", "work.acceptance"),
                ("res_id", "=", self.id),
                ("user_id", "=", user.id),
                ("activity_type_id", "=", act_type.id),
            ], limit=1)
            if existing:
                continue
            self.activity_schedule(
                act_type_xmlid=WA_REVIEW_ACT_TYPE_XMLID,
                user_id=user.id,
                summary=_("ตรวจรับพัสดุ: %s") % (self.name or ""),
            )

    def _cancel_review_activities(self):
        """Unlink pending review Todos for these WAs (no todo.log entry)."""
        act_type = self.env.ref(
            WA_REVIEW_ACT_TYPE_XMLID, raise_if_not_found=False
        )
        if not act_type:
            return
        self.env["mail.activity"].sudo().search([
            ("res_model", "=", "work.acceptance"),
            ("res_id", "in", self.ids),
            ("activity_type_id", "=", act_type.id),
        ]).unlink()
