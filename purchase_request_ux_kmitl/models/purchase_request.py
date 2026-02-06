# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    requested_by = fields.Many2one(
        comodel_name="res.users",
        domain="[('employee_ids.department_id', '=', department_id)]",
    )

    @api.onchange("department_id")
    def _onchange_department_id(self):
        self.requested_by = False

