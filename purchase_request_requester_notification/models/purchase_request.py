# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def write(self, vals):
        res = super().write(vals)

        if vals.get("state") == "to_approve":
            for request in self:
                request._on_state_to_approve()

        return res

    def _on_state_to_approve(self):
        self._schedule_to_approve_activity()
        self._send_to_approve_chatter_message()
        self._send_to_approve_email()

    def _schedule_to_approve_activity(self):
        self.ensure_one()

        activity_type = self._get_to_approve_activity_type()
        if not activity_type:
            return

        self.activity_schedule(
            activity_type_id=activity_type.id,
            summary=f"เอกสาร {self.name} รออนุมัติ",
            note=f"เอกสาร PR {self.name} รออนุมัติ เรื่อง {self.title}",
            user_id=self.requested_by.id,
        )

    def _get_to_approve_activity_type(self):
        return self.env.ref(
            "purchase_request_requester_notification.mail_act_purchase_request_notify_requester"
        )

    def _get_to_approve_email_template(self):
        return self.env.ref(
            "purchase_request_requester_notification.email_purchase_request_notify_requester"
        )

    def _send_to_approve_chatter_message(self):
        self.ensure_one()

        partner = self.requested_by.partner_id
        if not partner:
            return

        mention = self._build_partner_mention(partner)

        message = (
            f"{mention} เอกสาร PR <b>{self.name}</b> "
            f"เรื่อง <b>{self.title}</b> อยู่ในสถานะ <b>รออนุมัติ</b>"
        )

        self.message_post(
            body=message,
            message_type="notification",
            subtype_xmlid="mail.mt_comment",
            partner_ids=[partner.id],
        )

    def _build_partner_mention(self, partner):
        return (
            f'<span class="o_mail_partner" '
            f'data-oe-model="res.partner" data-oe-id="{partner.id}">'
            f'@{partner.name}</span>'
        )

    def _send_to_approve_email(self):
        template = self._get_to_approve_email_template()
        if template:
            template.send_mail(self.id, force_send=True)

