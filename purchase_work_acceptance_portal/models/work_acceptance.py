# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    is_current_user_committee = fields.Boolean(
        compute="_compute_is_current_user_committee",
        help="True when the current user is on this WA's committee. "
        "Non-stored, re-evaluated per viewer.",
    )

    @api.depends("work_acceptance_committee_ids.employee_id.user_id")
    @api.depends_context("uid")
    def _compute_is_current_user_committee(self):
        uid = self.env.uid
        for rec in self:
            user_ids = rec.work_acceptance_committee_ids.employee_id.user_id.ids
            rec.is_current_user_committee = uid in user_ids

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
