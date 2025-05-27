# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetProcurement(models.Model):
    _name = 'budget.procurement'
    _description = 'BudgetProcurement'

    name = fields.Char('Name')
    move_live_id = fields.Many2one(
        comodel_name="budget.move.line",
        string="Budget Move Line",
        required=True,
        index=True,
        auto_join=True,
        ondelete="cascade",
    )
