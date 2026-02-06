# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    requested_by = fields.Many2one(
        comodel_name="res.users",
        default=False,
    )

    @api.onchange("department_id")
    def _onchange_department_id(self):
        if self.requested_by and \
        self.requested_by.employee_ids.department_id != self.department_id:
            self.requested_by = False

        return {
            "domain": {
                "requested_by": [
                    ("employee_ids.department_id", "=", self.department_id.id)
                ]
            }
        }

