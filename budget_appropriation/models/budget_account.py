# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    deduct = fields.Boolean(default=False, tracking=True, string="หัก")
    default_deduct_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="หักให้หน่วยงาน",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
