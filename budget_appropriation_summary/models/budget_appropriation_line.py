# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriationLine(models.Model):
    _inherit = 'budget.appropriation.line'

    is_recurrent = fields.Boolean("เป็นงบประจำ", default=False, help="หากติ๊กเลือก, ระบบจะดึงจำนวนเงินไปรวมเป็นงบประจำ")
    is_ma = fields.Boolean("เป็นงบค่าดูแลและบำรุงรักษา", default=False, help="หากติ๊กเลือก, ระบบจะดึงจำนวนเงินไปรวมเป็นงบค่าดูแลและบำรุงรักษา")
    is_investment = fields.Boolean("เป็นงบลงทุน", default=False, help="หากติ๊กเลือก, ระบบจะดึงจำนวนเงินไปรวมเป็นงบลงทุน")
