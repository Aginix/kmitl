# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _cron_notify_contract_expire(self):
        today = fields.Date.today()
        notify_before_days = 15

        domain = [
            ('state', 'in', ['draft', 'purchase']),
            ('work_end', '>=', today),
            ('work_end', '<=', today + timedelta(days=notify_before_days)),
        ]

        purchase_orders = self.search(domain)

        if not purchase_orders:
            return

        action = self.env.ref('purchase_menu.action_contracts_expiring')
        odoobot_user = self.env.ref('base.user_root')
        users = self.env.ref('purchase.group_purchase_user').users
        body = _(
            'There are %s contracts that are about to expire.</b> '
            '<a href="/web#action=%s">Click to review</a>'
        ) % (len(purchase_orders), action.id)

        for user in users:
            # mail.channel.channel_get() return dict ที่มี key 'id'
            channel_data = self.env['mail.channel'].sudo().channel_get(
                [odoobot_user.partner_id.id, user.partner_id.id]
            )
            channel = self.env['mail.channel'].sudo().browse(channel_data['id'])

            channel.sudo().with_user(odoobot_user).message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                author_id=odoobot_user.partner_id.id,
            )