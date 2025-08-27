# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    def action_review(self):
        super().action_review()
        for line in self.line_ids:
            if line.procurement_plan:
                for procurement in line.procurement_plan_ids:
                    procurement.action_validate()

    def budget_move_line_vals(self):
        lines = super().budget_move_line_vals()
        for line in self.line_ids:
            if line.procurement_plan:
                for procurement in line.procurement_plan_ids:
                    procurement.action_pending()
                    vals = line.budget_move_line_vals()
                    vals['balance'] = procurement.total_price
                    vals['procurement_plan_analytic_id'] = procurement.analytic_account_id.id
                    vals['procurement_plan_id'] = procurement.id
                    lines.append(vals)
        return lines
