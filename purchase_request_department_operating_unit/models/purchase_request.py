# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.onchange("department_id")
    def _onchange_department_id(self):
        for rec in self:
            if rec.department_id and rec.department_id.operating_unit_id:
                rec.operating_unit_id = rec.department_id.operating_unit_id
            else:
                rec.operating_unit_id = False