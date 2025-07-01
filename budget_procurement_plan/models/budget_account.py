# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAccount(models.Model):
    _inherit = 'budget.account'

    procurement_plan = fields.Boolean(string="ทำแผนจัดซื้อจัดจ้าง",help="หากติ๊กถูก รหัสงบประมาณนี้จะต้องระบุเงินผ่านแผนจัดซื้อจัดจ้างเท่านั้น",default=False)
