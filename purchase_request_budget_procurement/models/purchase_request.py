# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    use_procurement_plan = fields.Boolean(
        string="เลือกใช้รายการจากแผนจัดซื้อจัดจ้าง", default=False
    )

    procurement_plan_id = fields.Many2one(
        comodel_name="procurement.plan", string="รายการแผนจัดซื้อจัดจ้าง", domain="", tracking=True
    )

    activity_analytic_id = fields.Many2one("account.analytic.account", store=True, compute="_compute_procurement_plan_analytic_id")
    department_analytic_id = fields.Many2one("account.analytic.account", store=True, compute="_compute_procurement_plan_analytic_id")
    fund_analytic_id = fields.Many2one("account.analytic.account", store=True, compute="_compute_procurement_plan_analytic_id")
    source_analytic_id = fields.Many2one("account.analytic.account", store=True, compute="_compute_procurement_plan_analytic_id")
    procurement_plan_analytic_id = fields.Many2one("account.analytic.account", store=True, compute="_compute_procurement_plan_analytic_id")

    @api.depends("state", "use_procurement_plan", "procurement_plan_id")
    def _compute_can_edit_budget(self):
        res = super()._compute_can_edit_budget()
        for rec in self:
            if rec.use_procurement_plan:
                rec.can_edit_budget = False

    @api.depends("use_procurement_plan", "procurement_plan_id")
    def _compute_procurement_plan_analytic_id(self):
        for rec in self:
            if rec.use_procurement_plan and rec.procurement_plan_id:
                rec.budget_account_id = rec.procurement_plan_id.budget_account_id.id
                rec.activity_analytic_id = rec.procurement_plan_id.activity_analytic_id.id
                rec.department_analytic_id = rec.procurement_plan_id.department_analytic_id.id
                rec.fund_analytic_id = rec.procurement_plan_id.fund_analytic_id.id
                rec.source_analytic_id = rec.procurement_plan_id.source_analytic_id.id
                rec.procurement_plan_analytic_id = rec.procurement_plan_id.procurement_plan_analytic_id.id
