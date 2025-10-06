# -*- coding: utf-8 -*-
import logging

from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = "budget.appropriation"

    procurement_plan_ids = fields.Many2many(
        comodel_name="procurement.plan",
        compute="_compute_procurement_plan_ids",
        string="รายการแผนจัดซื้อจัดจ้าง",
        store=False,
    )

    def _compute_procurement_plan_ids(self):
        for record in self:
            pass

    def action_review(self):
        super().action_review()
        for line in self.line_ids:
            if line.procurement_plan:
                for procurement in line.procurement_plan_ids:
                    procurement.action_validate()

    def action_post(self):
        self._create_procurement_plan()
        super().action_post()

    def _create_procurement_plan(self):
        for line in self.line_ids:
            if line.enable_procurement_plan:
                vals = line._prepare_procurement_plan_valus()
                procurement_plan = self.env['procurement_plan'].create(vals)
                line.procurement_plan_id = procurement_plan.id

                procurement_plan.action_validate()
                procurement_plan.action_pending()

    def budget_move_line_vals(self):
        lines = super().budget_move_line_vals()
        for line in self.line_ids:
            if line.enable_procurement_plan and line.procurement_plan_id:
                vals['procurement_plan_id'] = line.procurement_plan_id.id
        return lines
