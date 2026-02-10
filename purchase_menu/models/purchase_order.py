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
    
    expire_group_ids = fields.Many2many(
        'expire.group',
        string="Expire Groups",
        compute="_compute_expire_group_ids",
        store=True
    )

    @api.depends('work_end')
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for record in self:
            if record.work_end:
                record.days_to_expire = (record.work_end - today).days
            else:
                record.days_to_expire = 9999
    
    @api.depends('days_to_expire')
    def _compute_expire_group_ids(self):
        groups = self.env['expire.group'].search([])
        for record in self:
            matched_groups = groups.filtered(
                lambda g: g.min_days <= record.days_to_expire <= g.max_days
            )
            record.expire_group_ids = matched_groups
