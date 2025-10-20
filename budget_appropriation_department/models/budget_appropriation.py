# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    READONLY_STATES = {
        "review": [("readonly", True)],
        "posted": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    @api.model
    def _default_department(self):
        employee_id = self.env.user.employee_id
        if employee_id and employee_id.department_id:
            return employee_id.department_id.id
        return False

    department_id = fields.Many2one(
        string="Department",
        comodel_name="hr.department",
        default=lambda self: self._default_department(),
        readonly=False,
        states=READONLY_STATES,
    )

    def budget_move_vals(self):
        res = super().budget_move_vals()
        if self.department_id:
            res["department_id"] = self.department_id.id
        return res
