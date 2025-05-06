# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _name = "procurement.plan"
    _description = "Procurement Plan"
    _inherit = ["mail.thread"]

    date_range_fy_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
    )
    name = fields.Char("Name", required=True, tracking=True)
    amount = fields.Integer("Amount", required=True, tracking=True)
    unit = fields.Char("Unit of Measure", required=True, tracking=True)
    price_per_unit = fields.Float("Price per unit", required=True, tracking=True)
    total_price = fields.Float(
        "Total price",
        compute="_compute_total_price",
        store=True,
        readonly=True,
        tracking=True,
    )
    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method", string="Procurement Method", tracking=True
    )
    state = fields.Selection(
        [
            ("draft", "draft"),
            ("validate", "validate"),
            ("pending", "pending"),
            ("procurement", "procurement"),
            ("done", "done"),
        ],
        string="Status",
        readonly=True,
        default="draft",
        tracking=True,
    )
    purchase_request_eta = fields.Integer("Purchase Request (ETA)", tracking=True)
    procurement_announcement_eta = fields.Integer(
        "Procurement Announcement (ETA)", tracking=True
    )
    approval_signing_eta = fields.Integer("Approval Signing (ETA)", tracking=True)
    contract_order_signing_eta = fields.Integer(
        "Contract Order Signing (ETA)", tracking=True
    )
    acceptance_eta = fields.Integer("Acceptance (ETA)", tracking=True)
    payment_ids = fields.One2many(
        comodel_name="procurement.plan.payment", inverse_name="procurement_plan_id"
    )

    @api.depends("amount", "price_per_unit")
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.amount * record.price_per_unit
