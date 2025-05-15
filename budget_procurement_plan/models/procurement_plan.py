# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = 'procurement.plan'

    budget_template_line_id = fields.One2many(comodel_name='budget.template.line', inverse_name='template_id')
    budget_appropriation_line_id = fields.One2many(comodel_name="budget.appropriation.line",inverse_name='appropriation_id')

    appropriation_id = fields.Many2one(
        comodel_name='budget.appropriation',
        string='การจัดสรรงบประมาณ',
        compute='_compute_appropriation_id',
        store=False
    )

    @api.depends('appropriation_line_ids')
    def _compute_appropriation_id(self):
        for rec in self:
            line = rec.appropriation_line_ids[:1]
            rec.appropriation_id = line.appropriation_id if line else False

    appropriation_line_ids = fields.Many2many(
        comodel_name='budget.appropriation.line',
        string='รายการจัดสรรงบประมาณที่เชื่อมโยง'
    )
