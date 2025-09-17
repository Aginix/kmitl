# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    project_ids = fields.Many2many(
        comodel_name='budget.project',
        compute='_compute_project_ids',
        string='รายการแผนจัดซื้อจัดจ้าง',
        store=False,
    )

    def _compute_project_ids(self):
        for record in self:
            record.project_ids = record.line_ids.mapped('project_ids')

    def action_review(self):
        super().action_review()
        for line in self.line_ids:
            if line.is_project:
                for project in line.project_ids:
                    project.action_validate()

    def budget_move_line_vals(self):
        lines = super().budget_move_line_vals()
        for line in self.line_ids:
            if line.is_project:
                for project in line.project_ids:
                    project.action_pending()
                    vals = line.budget_move_line_vals()
                    vals['balance'] = project.amount
                    # vals['project_analytic_id'] = project.analytic_account_id.id
                    vals['project_id'] = project.id
                    lines.append(vals)
        return lines
