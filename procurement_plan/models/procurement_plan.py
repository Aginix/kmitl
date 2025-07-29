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

    @api.model
    def get_filter_options(self):
        """Get available options for filters"""
        # Get fiscal years that have budget appropriations
        fiscal_years = self.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )
        departments = self.env["account.analytic.account"].search([("root_plan_id.code", "=", "departments")], order="name")
        sources = self.env["account.analytic.account"].search([("root_plan_id.code", "=", "sources")], order="name")
        return {
            "fiscal_years": [
                {
                    "id": fy.id,
                    "name": fy.name,
                    "date_start": fy.date_from.strftime("%Y-%m-%d"),
                    "date_end": fy.date_to.strftime("%Y-%m-%d"),
                }
                for fy in fiscal_years
            ],
            "departments": [
                {
                    "id": dept.id,
                    "name": dept.name
                }
            for dept in departments
        ],
            "sources": [
                {
                    "id": source.id,
                    "name": source.name
                }
            for source in sources
        ],
        }
    @api.model
    def get_procurement_plan_data(self, filters):
        domain = []
        if filters.get("fiscal_year_id"):
            domain.append(("date_range_fy_id", "=", filters["fiscal_year_id"]))
        if filters.get("department_analytic_id"):
            domain.append(("department_analytic_id", "=", filters["department_analytic_id"]))
        if filters.get("source_analytic_id"):
            domain.append(("source_analytic_id", "=", filters["source_analytic_id"]))
        plans = self.search(domain)

        data = []
        for plan in plans:
            payment_list = []
            total_number_of_days = 0
            total_payment_amount = 0.0
            for payment in plan.payment_ids:
                payment_list.append({
                    "id": payment.id,
                    "number": payment.number,
                    "number_of_days": payment.number_of_days,
                    "month": payment.month,
                    "amount": payment.amount,
                    "state": payment.state,
                })
                total_number_of_days += payment.number_of_days or 0
                total_payment_amount += payment.amount or 0.0
            data.append({
                "id": plan.id,
                "name": plan.name,
                "fiscal_year": plan.date_range_fy_id.name if plan.date_range_fy_id else "",
                "department": plan.department_analytic_id.name if plan.department_analytic_id else "",
                "activity": plan.activity_analytic_id.name if plan.activity_analytic_id else "",
                "fund": plan.fund_analytic_id.name if plan.fund_analytic_id else "",
                "source": plan.source_analytic_id.name if plan.source_analytic_id else "",
                "amount": plan.amount,
                "unit": plan.unit,
                "price_per_unit": plan.price_per_unit,
                "total_price": plan.total_price,
                "procurement_method": plan.procurement_method_id.name if plan.procurement_method_id else "",
                "state": plan.state,
                "note": plan.note or "-",
                "purchase_request_eta": plan.purchase_request_eta,
                "procurement_announcement_eta": plan.procurement_announcement_eta,
                "approval_signing_eta": plan.approval_signing_eta,
                "contract_order_signing_eta": plan.contract_order_signing_eta,
                "acceptance_eta": plan.acceptance_eta,
                "payments": payment_list,
                "total_number_of_days": total_number_of_days,
                "total_payment_amount": total_payment_amount,
            })

        # ส่งกลับพร้อมสรุป
        return {
            "filters": filters,
            "records": data,
            "summary": {
                "total_amount": sum(p.total_price for p in plans),
                "plan_count": len(plans),
            },
        }
