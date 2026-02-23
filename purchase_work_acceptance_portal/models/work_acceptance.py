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
            order_url = wa.purchase_id.get_portal_link()
            wa_url = wa.get_portal_link()
            for committee in wa.work_acceptance_committee_ids:
                user = committee.employee_id.user_id
                if not user:
                    continue
                message = (
                    f"<a href='{wa_url}&committee_token={committee.access_token}'>กรุณาตรวจรับพัสดุ</a><br/>"
                    f"<a href='{order_url}&wa_token={wa.access_token}'>เอกสารสัญญา</a>"
                )
                Inbox = self.env["work.acceptance.inbox"].sudo()
                existing = Inbox.search(
                    [("user_id", "=", user.id), ("work_acceptance_id", "=", wa.id)],
                    limit=1,
                )
                if existing:
                    existing.write({"message": message, "is_read": False})
                else:
                    Inbox.create({"user_id": user.id, "work_acceptance_id": wa.id, "message": message})
                self.env["bus.bus"]._sendone(
                    user.partner_id,
                    "work_acceptance/inbox",
                    {"refresh": True, "wa_name": wa.name, "wa_id": wa.id},
                )
        return res
