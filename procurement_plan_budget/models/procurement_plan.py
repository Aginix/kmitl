# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _name = 'procurement.plan'
    _inherit = ['procurement.plan']

    READONLY_STATES = {
        "validate": [("readonly", True)],
        "pending": [("readonly", True)],
        "procurement": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    budget_appropriation_id = fields.Many2one('budget.appropriation', related='budget_appropriation_line_id.appropriation_id', store=True, readonly=True)
    budget_appropriation_line_id = fields.Many2one('budget.appropriation.line')
    budget_account_id = fields.Many2one('budget.account', string="รหัสงบประมาณ", states=READONLY_STATES)
    activity_analytic_id = fields.Many2one(states=READONLY_STATES)
    department_analytic_id = fields.Many2one(states=READONLY_STATES)
    fund_analytic_id = fields.Many2one(states=READONLY_STATES)
    source_analytic_id = fields.Many2one(states=READONLY_STATES)
