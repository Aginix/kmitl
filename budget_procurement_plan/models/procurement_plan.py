# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    budget_account_id = fields.Many2one(
        string="รหัสงบประมาณ", comodel_name="budget.account"
    )
    budget_move_id = fields.Many2one(string="Budget Move", comodel_name="budget.move")
    budget_move_line_id = fields.Many2one(
        string="Budget Move Live", comodel_name="budget.move.line"
    )
