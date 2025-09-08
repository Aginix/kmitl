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

    def action_view_procurement_plan(self):
        self.ensure_one()
        if not self.procurement_plan_id:
            return {"type": "ir.actions.act_window_close"}
        
        return {
            "type": "ir.actions.act_window",
            "res_model": "procurement.plan",
            "view_mode": "form",
            "res_id": self.procurement_plan_id.id,
            "target": "current",
        }


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    purchase_request_count = fields.Integer(
        string="Purchase Requests Count",
        compute="_compute_purchase_request_count"
    )

    @api.depends("purchase_request_ids")
    def _compute_purchase_request_count(self):
        for record in self:
            record.purchase_request_count = len(record.purchase_request_ids)

    purchase_request_ids = fields.One2many(
        comodel_name="purchase.request",
        inverse_name="procurement_plan_id",
        string="Purchase Requests"
    )

    def action_view_purchase_requests(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("purchase_request.purchase_request_form_action")
        if len(self.purchase_request_ids) > 1:
            action["domain"] = [("id", "in", self.purchase_request_ids.ids)]
        elif len(self.purchase_request_ids) == 1:
            form_view = [(self.env.ref("purchase_request.view_purchase_request_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [(state, view) for state, view in action["views"] if view != "form"]
            else:
                action["views"] = form_view
            action["res_id"] = self.purchase_request_ids.ids[0]
        else:
            action = {"type": "ir.actions.act_window_close"}
        context = {
            "default_use_procurement_plan": True,
            "default_procurement_plan_id": self.id,
        }
        action["context"] = context
        return action
