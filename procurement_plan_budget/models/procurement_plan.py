# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from procurement_plan import ProcurementPlan

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = 'procurement.plan'

    budget_account_id = fields.Many2one('budget.account')
    activity_analytic_id = fields.Many2one(required=True, states=ProcurementPlan.READONLY_STATES)
    department_analytic_id = fields.Many2one(required=True, states=ProcurementPlan.READONLY_STATES)
    fund_analytic_id = fields.Many2one(required=True, states=ProcurementPlan.READONLY_STATES)
    source_analytic_id = fields.Many2one(required=True, states=ProcurementPlan.READONLY_STATES)
