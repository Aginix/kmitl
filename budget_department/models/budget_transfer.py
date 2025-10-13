# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetTransfer(models.Model):
    _inherit = 'budget.transfer'

    @api.model
    def _default_department(self):
        employee_id = self.env.user.employee_id
        if employee_id and employee_id.deparment_id:
            return employee_id.deparment_id.id
        return False

    department_id = fields.Many2one(string="Department", comodel_name="hr.department", default=lambda self: self._default_department())

    def _prepare_budget_move_vals(self):
        vals = super()._prepare_budget_move_vals()
        if self.department_id:
            vals['department_id'] = self.department_id.id
        return vals
