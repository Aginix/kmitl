# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _name = "procurement.plan"
    _description = "Procurement Plan"
    _inherit = ["mail.thread", "analytic.distribution.mixin"]

    READONLY_STATES = {
        "validate": [("readonly", True)],
        "pending": [("readonly", True)],
        "procurement": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
    )
    name = fields.Char("Name", required=True, tracking=True, states=READONLY_STATES)
    amount = fields.Integer(
        "Amount", required=True, tracking=True, states=READONLY_STATES
    )
    unit = fields.Char(
        "Unit of Measure", required=True, tracking=True, states=READONLY_STATES
    )
    price_per_unit = fields.Float(
        "Price per unit", required=True, tracking=True, states=READONLY_STATES
    )
    total_price = fields.Float(
        "Total price",
        compute="_compute_total_price",
        store=True,
        readonly=True,
        tracking=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validate", "To Approve"),
            ("pending", "Pending"),
            ("procurement", "Procurement"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
        default="validate",
        tracking=True,
    )
    note = fields.Text("Notes", tracking=True, states=READONLY_STATES)
    purchase_request_eta = fields.Integer(
        "Purchase Request (ETA)", tracking=True, states=READONLY_STATES
    )
    procurement_announcement_eta = fields.Integer(
        "Procurement Announcement (ETA)", tracking=True, states=READONLY_STATES
    )
    approval_signing_eta = fields.Integer(
        "Approval Signing (ETA)", tracking=True, states=READONLY_STATES
    )
    contract_order_signing_eta = fields.Integer(
        "Contract Order Signing (ETA)", tracking=True, states=READONLY_STATES
    )
    acceptance_eta = fields.Integer(
        "Acceptance (ETA)", tracking=True, states=READONLY_STATES
    )
    payment_ids = fields.One2many(
        comodel_name="procurement.plan.payment",
        inverse_name="procurement_plan_id",
        states=READONLY_STATES,
    )

    activity_analytic_id = fields.Many2one(states=READONLY_STATES)
    department_analytic_id = fields.Many2one(states=READONLY_STATES)
    fund_analytic_id = fields.Many2one(states=READONLY_STATES)
    source_analytic_id = fields.Many2one(states=READONLY_STATES)

    @api.depends("amount", "price_per_unit")
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.amount * record.price_per_unit
