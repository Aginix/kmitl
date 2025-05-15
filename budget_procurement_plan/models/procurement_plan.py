# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = 'procurement.plan'

    budget_template_line_id = fields.One2many(comodel_name='budget.template.line', inverse_name='template_id')
    budget_appropriation_line_id = fields.One2many(comodel_name="budget.appropriation.line",inverse_name='appropriation_id')
