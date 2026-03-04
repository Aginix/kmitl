# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AnalyticDistributionMixin(models.AbstractModel):
    _inherit = 'analytic.distribution.mixin'

    procurement_plan_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แผนจัดซื้อจัดจ้าง",
        compute="_compute_procurement_plan_analytic_id",
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "procurement_plan")],
    )

    def _analytic_fields(self):
        fields = super()._analytic_fields()
        fields.append('procurement_plan_analytic_id')
        return fields

    @api.depends("procurement_plan_analytic_id")
    def _compute_procurement_plan_analytic_id(self):
        super()._compute_analytic_distribution()

    def _analytic_keys(self):
        res = super()._analytic_keys()
        res['procurement_plan'] = 'procurement_plan_analytic_id'
        return res
