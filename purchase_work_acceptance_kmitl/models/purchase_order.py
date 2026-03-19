# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_view_wa(self):
        result = super().action_view_wa()
        result["context"]["default_late_days"] = self.late_days
        result["context"]["default_fines_rate"] = self.fines_rate
        return result
