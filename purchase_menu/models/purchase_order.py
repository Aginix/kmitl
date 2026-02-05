# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    days_to_expire = fields.Integer(
        string="Days to Expire",
        compute="_compute_days_to_expire"
    )

    @api.depends('work_end')
    def _compute_days_to_expire(self):
        today = fields.Date.today()
        for record in self:
            if record.work_end:
                record.days_to_expire = (record.work_end - today).days
            else:
                record.days_to_expire = 9999