# -*- coding: utf-8 -*-
import logging

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

    @api.depends('days_to_expire')
    def _compute_days_to_expire_display(self):
        for record in self:
            record.days_to_expire_display = str(record.days_to_expire) if record.days_to_expire else ''

    @api.depends('work_end')
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for record in self:
            if record.work_end:
                record.days_to_expire = (record.work_end - today).days
            else:
                record.days_to_expire = 9999
    
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
