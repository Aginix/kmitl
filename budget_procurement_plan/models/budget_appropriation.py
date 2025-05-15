# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    procurement_plan_ids = fields.Many2many(
        comodel_name='procurement.plan',
        compute='_compute_procurement_plans_m2m',
        string='แผนจัดซื้อจัดจ้างทั้งหมด',
        store=False,
    )

    def _compute_procurement_plans_m2m(self):
        for rec in self:
            plans = rec.line_ids.mapped('procurement_plan_ids')
            rec.procurement_plan_ids = plans
