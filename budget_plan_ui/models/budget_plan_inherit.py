# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class BudgetPlanInherit(models.Model):
    _inherit = "budget.plan"

    budget_type = fields.Selection(
        related="template_id.budget_type", string="Budget Type", store=True
    )

    def action_open_edit_budet(self):
        session = request.session
        session.update({"budget_template_id": self.template_id.id})

        if self.budget_type == "expense":
            return {
                "type": "ir.actions.client",
                "name": "Expense Budget",
                "tag": "expense_budget",
            }

        if self.budget_type == "revenue":
            return {
                "type": "ir.actions.client",
                "name": "Revenue Budget",
                "tag": "revenue_budget",
            }

    @api.model
    def get_id(self):
        session = request.session
        budget_id = session.get("budget_template_id")
        return budget_id or 0
