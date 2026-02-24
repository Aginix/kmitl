# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _domain_contract_expiration(self):
        today = fields.Date.today()
        notify_before_days = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'purchase_order_notification.notify_before_days',
                default=15,
            )
        )
        return [
            ('state', 'in', ['draft', 'purchase']),
            ('work_end', '>=', today),
            ('work_end', '<=', today + timedelta(days=notify_before_days)),
        ]

    def _cron_notify_contract_expire(self):
        purchase_orders = self.search(self._domain_contract_expiration())

        if not purchase_orders:
            return

        action = self.env.ref('purchase_menu.action_contracts_expiring')
        odoobot_user = self.env.ref('base.user_root')
        orders_by_user = {}

        for order in purchase_orders:
            if not order.user_id:
                continue
            orders_by_user.setdefault(order.user_id, self.env['purchase.order'])
            orders_by_user[order.user_id] |= order

        for user, orders in orders_by_user.items():
            body = _(
                'There are %s contracts that are about to expire. '
                '<a href="/web#action=%s">Click to review</a>'
            ) % (len(orders), action.id)
            
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