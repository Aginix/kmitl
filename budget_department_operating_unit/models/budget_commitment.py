# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    _inherit = 'budget.commitment'

    operating_unit_id = fields.Many2one(compute="_compute_operating_unit_id", store=True)

    @api.depends("department_id")
    def _compute_operating_unit_id(self):
        for rec in self:
            if rec.department_id and rec.department_id.operating_unit_id:
                rec.operating_unit_id = rec.department_id.operating_unit_id.id
            else:
                rec.operating_unit_id = False
