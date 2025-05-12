# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    procurement_ids = fields.One2many(
        comodel_name="procurement.plan",
        compute="_compute_procurement_ids",
        string="Related Procurement Plans",
    )

    @api.depends("line_ids.procurement_plan_ids")
    def _compute_procurement_ids(self):
        for record in self:
            procurement_set = self.env["procurement.plan"]
            for line in record.line_ids:
                procurement_set |= line.procurement_plan_ids
            record.procurement_ids = procurement_set
