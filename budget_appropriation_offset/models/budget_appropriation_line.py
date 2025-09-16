# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = "budget.appropriation.line"

    offset_ids = fields.One2many(
        comodel_name="budget.appropriation.offset",
        inverse_name="appropriation_line_id",
        string="รายการหักโอน",
    )

    offset_total = fields.Float(
        string="จำนวนเงินหักโอนทั้งหมด",
        store=False,
        required=False,
        compute="_compute_offset_total",
    )

    def budget_move_line_vals(self):
        vals = super().budget_move_line_vals()
        if self.procurement_plan.offset_ids:
            # TODO: ต้องหักลบงบประมาณ
            pass
        return vals

    def _compute_offset_total(self):
        for rec in self.filtered("offset_ids"):
            rec.offset_total = sum(rec.offset_ids.mapped("amount"))
