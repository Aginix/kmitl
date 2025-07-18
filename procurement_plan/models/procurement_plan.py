import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

MONTH_SELECTION = [
    ("1", "January"),
    ("2", "February"),
    ("3", "March"),
    ("4", "April"),
    ("5", "May"),
    ("6", "June"),
    ("7", "July"),
    ("8", "August"),
    ("9", "September"),
    ("10", "October"),
    ("11", "November"),
    ("12", "December"),
]


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
        comodel_name="account.fiscal.year", string="Fiscal year", states=READONLY_STATES
    )
    name = fields.Char(required=True, tracking=True,)
    amount = fields.Integer(required=True, tracking=True,)
    unit = fields.Char(
        "Unit of Measure", required=True, tracking=True,
    )
    price_per_unit = fields.Float(
        "Price per unit", required=True, tracking=True,
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
        default="draft",
        tracking=True,
    )
    note = fields.Text("Notes", tracking=True, states=READONLY_STATES)
    purchase_request_eta = fields.Selection(
        MONTH_SELECTION, "Purchase Request (ETA)", tracking=True, states=READONLY_STATES
    )
    procurement_announcement_eta = fields.Selection(
        MONTH_SELECTION,
        "Procurement Announcement (ETA)",
        tracking=True,
        states=READONLY_STATES,
    )
    approval_signing_eta = fields.Selection(
        MONTH_SELECTION, "Approval Signing (ETA)", tracking=True, states=READONLY_STATES
    )
    contract_order_signing_eta = fields.Selection(
        MONTH_SELECTION,
        "Contract Order Signing (ETA)",
        tracking=True,
        states=READONLY_STATES,
    )
    acceptance_eta = fields.Selection(
        MONTH_SELECTION, "Acceptance (ETA)", tracking=True, states=READONLY_STATES
    )
    payment_ids = fields.One2many(
        comodel_name="procurement.plan.payment",
        inverse_name="procurement_plan_id",
        states=READONLY_STATES,
    )

    activity_analytic_id = fields.Many2one(states=READONLY_STATES)
    department_analytic_id = fields.Many2one(required=True, states=READONLY_STATES)
    fund_analytic_id = fields.Many2one(states=READONLY_STATES)
    source_analytic_id = fields.Many2one(required=True, states=READONLY_STATES)

    @api.depends("amount", "price_per_unit")
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.amount * record.price_per_unit
