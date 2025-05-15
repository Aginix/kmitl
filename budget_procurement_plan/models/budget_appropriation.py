# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    from odoo import api, fields, models

class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    procurement_plan_ids = fields.Many2many(
        comodel_name='procurement.plan',
        compute='_compute_procurement_plans',
        string="แผนจัดซื้อจัดจ้าง (ทั้งหมดจากรายการจัดสรร)",
        store=True,
    )

    @api.depends('line_ids.procurement_plan_ids')
    def _compute_procurement_plans(self):
        for rec in self:
            rec.procurement_plan_ids = rec.line_ids.mapped('procurement_plan_ids')
