# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    def action_post(self):
        super().action_post()
        self._create_budget_project()

    def _create_budget_project(self):
        for line in self.line_ids.filtered('enable_project'):
            self.env['kmitl.project'].create({
                # TODO: change date_range_fy_id to account_fiscal_year_id
                "account_fiscal_year_id": line.appropriation_id.date_range_fy_id.id,
                "name": line.description,
                "project_type": line.project_type,
                "user_id": line.appropriation_id.user_id.id,
                "creating_user_id": line.appropriation_id.user_id.id,
                "analytic_distribution": line.analytic_distribution,
            })
