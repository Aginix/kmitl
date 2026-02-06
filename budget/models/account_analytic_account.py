# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    budgetable = fields.Boolean(
        tracking=True,
        copy=True,
        default=False,
        help="ติ๊กถูกเพื่อระบุว่ารหัสค่าใช้จ่ายสามารถจัดสรรงบประมาณได้",
    )
