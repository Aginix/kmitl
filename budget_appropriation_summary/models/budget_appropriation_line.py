# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = 'budget.appropriation.line'

    is_recurrent = fields.Boolean("เป็นงบประจำ", default=False, help="หากติ๊กเลือก, ระบบจะดึงจำนวนเงินไปรวมเป็นงบประจำ")
