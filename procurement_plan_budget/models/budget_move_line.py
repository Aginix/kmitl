# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

    procurement_plan = fields.Boolean(
        related="account_id.procurement_plan",
        store=True,
        readonly=True,
    )

    procurement_plan_id = fields.Many2one(comodel_name="procurement.plan", string="รายการแผนจัดซื้อจัดจ้าง")
