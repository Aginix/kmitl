# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetTemplateLine(models.Model):
    _inherit = 'budget.template.line'

    procurement_plan = fields.Boolean(string="ทำแผนจัดซื้อจัดจ้าง",help="หากติ๊กถูก รหัสงบประมาณนี้จะต้องระบุเงินผ่านแผนจัดซื้อจัดจ้างเท่านั้น",default=False)
