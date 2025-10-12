# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetTransfer(models.Model):
    _inherit = 'budget.transfer'

    @api.model
    def _default_department(self):
        department_id = False
        employee = self.env.user.employee_ids
        if employee and employee[0].department_id:
            department_id = employee[0].department_id.id
        return department_id

    department_id = fields.Many2one(string="Department", comodel_name="hr.department", default=lambda self: self._default_department())
