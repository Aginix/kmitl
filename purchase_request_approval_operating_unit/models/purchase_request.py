# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def _prepare_approval_vals(self):
        vals = super()._prepare_approval_vals()

        vals.update({
            "operating_unit_id": self.operating_unit_id.id,
            "requesting_operating_unit_id": self.department_id.operating_unit_id.id,
        })
        
        return vals
