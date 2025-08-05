# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMove(models.Model):
    _inherit = 'budget.move'

    budget_project_ids = fields.One2many(
        "budget.project",
        "budget_move_line_id",
        compute='_compute_budget_project_ids',
        string="Projects/Activities",
        domain=[("budget_move_line_id.is_virtual_line", "=", False)],
    )

    def _compute_budget_project_ids(self):
        for record in self:
            record.budget_project_ids = record.line_ids.mapped('budget_project_ids')
