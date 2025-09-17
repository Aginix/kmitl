# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    offset_ids = fields.One2many(
        comodel_name="budget.appropriation.offset",
        compute='_compute_offset_ids',
        # inverse_name="appropriation_id",
        string="รายการหักโอน",
    )

    offset_total = fields.Float(
        string="จำนวนเงินหักโอนทั้งหมด",
        store=False,
        required=False,
        compute="_compute_offset_total",
    )

    total_revenue_net = fields.Float(
        string="รายรับสุทธิ",
        store=False,
        required=False,
        compute="_compute_total_revenue_net",
    )

    @api.depends('line_ids.offset_ids', 'line_ids.offset_ids.amount')
    def _compute_offset_ids(self):
        for record in self:
            if record.budget_type == 'revenue':
                record.offset_ids = record.line_ids.mapped('offset_ids')
            else:
                record.offset_ids = False

    @api.depends('line_ids.offset_ids', 'line_ids.offset_ids.amount')
    def _compute_offset_total(self):
        for record in self:
            if record.budget_type == 'revenue':
                record.offset_total = sum(record.offset_ids.mapped("amount"))
            else:
                record.offset_total = False

    @api.depends('line_ids.offset_ids', 'line_ids.offset_ids.amount', 'total_amount')
    def _compute_total_revenue_net(self):
        for record in self:
            if record.budget_type == 'revenue':
                record.total_revenue_net = record.total_amount - record.offset_total
            else:
                record.total_revenue_net = False
