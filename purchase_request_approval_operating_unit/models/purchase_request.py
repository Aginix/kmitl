# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def _prepare_approval_vals(self):
        # สร้าง PR2 จาก PR1 ให้คัดลอก OU ไปด้วย
        vals = super()._prepare_approval_vals()
        vals['operating_unit_id'] = self.operating_unit_id.id
        return vals
