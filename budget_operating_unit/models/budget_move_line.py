# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMoveLine(models.Model):
    _inherit = 'budget.move.line'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="move_id.operating_unit_id",
        string="Operating Unit",
    )
