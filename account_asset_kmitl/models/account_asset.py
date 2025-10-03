# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string = "Fiscal year"
    )

    gpsc_id =  fields.Many2one(
        "procurement.gpsc",
        string = "GPSC Id"
    )

    department_id = fields.Many2one(
        "hr.department",
        related='operating_unit_id.department_id',
        string = "Department"
    )