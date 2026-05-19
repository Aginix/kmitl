# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    days_to_expire = fields.Integer(
        string="Days to Expire",
        compute="_compute_days_to_expire",
        store=True
    )
    
    expire_range = fields.Selection([
        ('0-15', '0-15 Days'),
        ('16-30', '16-30 Days'),
        ('31-60', '31-60 Days'),
        ('60+', 'Morethan 60 Days'),
    ], string="Expire Range", compute="_compute_expire_range", store=True)

    days_to_expire_display = fields.Char(
        string="Days to Expire",
        compute="_compute_days_to_expire_display",
        store=False
    )

    def action_recompute_expire(self):
        records = self.search([('work_end', '!=', False)])
        records._compute_days_to_expire()
        records._compute_expire_range()

    @api.depends('work_end', 'days_to_expire')
    def _compute_days_to_expire_display(self):
        for record in self:
            record.days_to_expire_display = str(record.days_to_expire) if record.work_end else ''

    @api.depends('work_end')
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for record in self:
            if record.work_end:
                record.days_to_expire = (record.work_end - today).days
            else:
                record.days_to_expire = 0
    
    @api.depends('days_to_expire')
    def _compute_expire_range(self):
        for record in self:
            days = record.days_to_expire
            if days <= 15:
                record.expire_range = '0-15'
            elif days <= 30:
                record.expire_range = '16-30'
            elif days <= 60:
                record.expire_range = '31-60'
            else:
                record.expire_range = '60+'

    # Notification
    def _domain_contract_expiration(self):
        today = fields.Date.today()
        notify_before_days = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'purchase_order_expiration.notify_before_days',
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

        action = self.env.ref('purchase_order_expiration.action_contracts_expiring')
        odoobot_user = self.env.ref('base.user_root')
        orders_by_user = {}

        for order in purchase_orders:
            if not order.user_id:
                continue
            orders_by_user.setdefault(order.user_id, self.env['purchase.order'])
            orders_by_user[order.user_id] |= order

        for user, orders in orders_by_user.items():
            if user == odoobot_user:
                continue
            body = _(
                'There are %s contracts that are about to expire. '
                '<a href="/web#action=%s">Click to review</a>'
            ) % (len(orders), action.id)
            try:
                with self.env.cr.savepoint():
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
            except Exception:
                _logger.warning(
                    "Failed to notify user %s of expiring contracts", user.name, exc_info=True
                )
