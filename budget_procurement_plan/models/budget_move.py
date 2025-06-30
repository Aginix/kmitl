# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMove(models.Model):
    _inherit = 'budget.move'

    procurement_plan_ids = fields.Many2many(
        comodel_name='procurement.plan',
        compute='_compute_procurement_plan_ids',
        string='แผนจัดซื้อจัดจ้างทั้งหมด',
        store=False,
    )
    
    budget_type = fields.Selection(
        related='journal_id.default_budget_type',
        string='Budget Type',
        store=False,
        readonly=True,
    )

    def _compute_procurement_plan_ids(self):
        for record in self:
            record.procurement_plan_ids = record.line_ids.mapped('procurement_plan_ids')
