# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = 'budget.appropriation.line'

    note = fields.Text()

    procurement_plan_ids = fields.One2many(
        "procurement.plan",
        "budget_plan_line_id",
        string="Procurement Plans",
    )
