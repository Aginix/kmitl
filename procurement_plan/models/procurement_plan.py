import logging

from odoo import _, api, fields, models

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
    _inherit = ["mail.thread"]
    _check_company_auto = True
    _rec_name = "description"
    _rec_names_search = ["name", "description"]

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
        required=True,
        states=READONLY_STATES,
    )
    name = fields.Char(
        string="รหัสเอกสาร",
        compute="_compute_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
    )
    description = fields.Char(
        string="ชื่อรายการ",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    amount = fields.Integer(
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    unit = fields.Char(
        "Unit of Measure",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    price_per_unit = fields.Float(
        "Price per unit",
        required=True,
        tracking=True,
        states=READONLY_STATES,
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
        copy=False,
        default="draft",
        tracking=True,
    )
    note = fields.Text("Notes", tracking=True, states=READONLY_STATES)
    purchase_request_eta = fields.Selection(
        MONTH_SELECTION,
        "Purchase Request (ETA)",
        tracking=True,
    )
    procurement_announcement_eta = fields.Selection(
        MONTH_SELECTION, "Procurement Announcement (ETA)", tracking=True
    )
    approval_signing_eta = fields.Selection(
        MONTH_SELECTION,
        "Approval Signing (ETA)",
        tracking=True,
    )
    contract_order_signing_eta = fields.Selection(
        MONTH_SELECTION, "Contract Order Signing (ETA)", tracking=True
    )
    acceptance_eta = fields.Selection(
        MONTH_SELECTION,
        "Acceptance (ETA)",
        tracking=True,
    )
    payment_ids = fields.One2many(
        comodel_name="procurement.plan.payment", inverse_name="procurement_plan_id"
    )
    user_id = fields.Many2one(
        string="User",
        comodel_name="res.users",
        copy=False,
        default=lambda self: self.env.user,
        store=True,
        tracking=True,
        readonly=False,
        states=READONLY_STATES,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )

    @api.depends("state", "name")
    def _compute_name(self):
        self = self.sorted(lambda m: m.id)

        for record in self:
            if record.state == "cancel":
                continue

            record_has_name = record.name and record.name != "New"
            if record_has_name or (
                record.state not in ("pending", "procurement", "done")
            ):
                continue
            if not record_has_name:
                record.name = self.env["ir.sequence"].next_by_code(
                    "procurement.plan"
                ) or _("New")

    @api.depends("amount", "price_per_unit")
    def _compute_total_price(self):
        for record in self:
            record.total_price = record.amount * record.price_per_unit

    def action_validate(self):
        self.write({"state": "validate"})

    def action_pending(self):
        self.write({"state": "pending"})

    def action_procurement(self):
        self.write({"state": "procurement"})

    def action_done(self):
        self.write({"state": "done"})
