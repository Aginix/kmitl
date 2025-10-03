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
        odoobot = self.env.ref("base.partner_root")
        for wa in self:
            purchase = wa.purchase_id
            order_url = purchase.get_portal_link()
            if wa.work_acceptance_committee_ids:
                for committee in wa.work_acceptance_committee_ids:
                    wa_url = wa.get_portal_link()
                    message = f"กรุณาตรวจรับพัสดุที่มีชื่อว่า {wa.name} \n เอกสารสัญญา/ใบสั่งซื้อ/จ้าง : <a href='{order_url+'&committee_id='+str(committee.id)}'>คลิกที่นี่</a> \n เอกสารตรวจรับ : <a href='{wa_url+'&committee_token='+str(committee.access_token)}'>คลิกที่นี่</a>"
                    channel = self.env['mail.channel'].channel_get([committee.employee_id.user_id.partner_id.id])
                    channel_id = self.env['mail.channel'].browse(channel["id"])
                    channel_id.message_post(
                    body=message,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    )
        return res
