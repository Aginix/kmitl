# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    def get_portal_link(self):
        self.ensure_one()
        self._portal_ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/wa/view/{self.id}?access_token={self.access_token}"

    def request_validation(self):
        res = super().request_validation()
        for wa in self:
            if not wa.work_acceptance_committee_ids:
                continue
            for committee in wa.work_acceptance_committee_ids:
                user = committee.employee_id.user_id
                if not user:
                    continue
                Inbox = self.env["work.acceptance.inbox"].sudo()
                existing = Inbox.search(
                    [("user_id", "=", user.id), ("work_acceptance_id", "=", wa.id)],
                    limit=1,
                )
                if not existing:
                    Inbox.create({"user_id": user.id, "work_acceptance_id": wa.id})
                self.env["bus.bus"]._sendone(
                    user.partner_id,
                    "work_acceptance/inbox",
                    {"refresh": True, "wa_name": wa.name, "wa_id": wa.id},
                )
        return res
