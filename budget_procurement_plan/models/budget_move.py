# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
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

    @api.constrains('appropriation_line_ids')
    def _check_negative_unallocated_balance(self):
        for record in self:
            negative_lines = record.appropriation_line_ids.filtered(
                lambda l: l.unallocated_balance < 0
            )
            if negative_lines:
                raise ValidationError(
                    "พบรายการที่ยอดเงินยังไม่ระบุ (Unallocated Balance) เป็นค่าติดลบ:\n%s" % (
                        "\n".join(f"- {line.display_name or line.id}: {line.unallocated_balance}" for line in negative_lines)
                    )
                )
