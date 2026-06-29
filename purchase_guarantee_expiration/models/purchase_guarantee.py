# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

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
        records = self.search([('date_due_guarantee', '!=', False)])
        records._compute_days_to_expire()
        records._compute_expire_range()

    @api.depends('date_due_guarantee', 'days_to_expire')
    def _compute_days_to_expire_display(self):
        for record in self:
            record.days_to_expire_display = str(record.days_to_expire) if record.date_due_guarantee else ''

    @api.depends('date_due_guarantee')
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for record in self:
            if record.date_due_guarantee:
                record.days_to_expire = (record.date_due_guarantee - today).days
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
    def _domain_guarantee_expiration(self):
        today = fields.Date.today()
        notify_before_days = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'purchase_guarantee_expiration.notify_before_days',
                default=15,
            )
        )
        return [
            ('state', '=', 'draft'),
            ('date_return', '=', False),
            ('date_due_guarantee', '>=', today),
            ('date_due_guarantee', '<=', today + timedelta(days=notify_before_days)),
        ]

    def _cron_notify_guarantee_expire(self):
        guarantees = self.search(self._domain_guarantee_expiration())

        if not guarantees:
            return

        activity_type = self.env.ref(
            'purchase_guarantee_expiration.mail_activity_type_guarantee_expiring'
        )

        for guarantee in guarantees:
            user = guarantee.purchase_id.user_id or guarantee.requisition_id.user_id
            if not user:
                continue
            existing = self.env['mail.activity'].search_count([
                ('res_model', '=', guarantee._name),
                ('res_id', '=', guarantee.id),
                ('activity_type_id', '=', activity_type.id),
                ('user_id', '=', user.id),
            ])
            if existing:
                continue
            try:
                with self.env.cr.savepoint():
                    guarantee.activity_schedule(
                        act_type_xmlid='purchase_guarantee_expiration.mail_activity_type_guarantee_expiring',
                        user_id=user.id,
                        date_deadline=guarantee.date_due_guarantee,
                        summary=_('Purchase Guarantee %s expires in %s day(s)') % (
                            guarantee.name, guarantee.days_to_expire
                        ),
                    )
            except Exception:
                _logger.warning(
                    "Failed to schedule expiry activity for guarantee %s",
                    guarantee.name,
                    exc_info=True,
                )
