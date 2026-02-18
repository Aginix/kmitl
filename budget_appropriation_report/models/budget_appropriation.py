# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    treasury_replenishment_amount = fields.Monetary(
        string="ชดใช้เงินคงคลัง",
        currency_field='currency_id',
        readonly=False,
        states=READONLY_STATES,
        compute='_compute_totals',
    )

    deducted_reserve_amount = fields.Monetary(
        string="หักเงินสำรอง",
        currency_field='currency_id',
        readonly=False,
        states=READONLY_STATES,
        compute='_compute_totals',
    )

    recurrent_budget_amount = fields.Monetary(
        string="งบประจำ",
        currency_field='currency_id',
        readonly=False,
        states=READONLY_STATES,
        compute='_compute_totals',
    )

    external_funding_amount = fields.Monetary(
        string="เงินสนับสนุนจากหน่วยงานภายนอก",
        currency_field='currency_id',
        readonly=False,
        states=READONLY_STATES,
        compute='_compute_totals',
    )

    @api.depends('appropriation_line_ids.code', 'appropriation_line_ids.balance')
    def _compute_totals(self):
        for record in self:
            record.treasury_replenishment_amount = 0
            record.deducted_reserve_amount = 0
            record.recurrent_budget_amount = 0
            record.external_funding_amount = 0
