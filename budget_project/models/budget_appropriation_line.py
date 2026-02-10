# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    is_project = fields.Boolean(
        related="account_id.is_project",
        store=True,
    )

    enable_project = fields.Boolean(default=False)

    project_type = fields.Selection(related="account_id.project_type", store=True)

    @api.depends("enable_project")
    def _compute_highlight_row(self):
        super()._compute_highlight_row()
        for rec in self:
            if rec.enable_project:
                rec.highlight_row = True
