# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAccount(models.Model):
    _inherit = 'budget.account'

    procurement_plan = fields.Boolean(string="ทำแผนจัดซื้อจัดจ้าง",help="ติ๊กถูกเพื่อระบุว่าเป็นประเภทงบลงทุน จะสามารถจัดสรรแผนจัดซื้อจัดจ้างได้",default=False)
