import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

CLIENT_ORG_TYPE_SELECTION = [
    ("government", "Government"),
    ("state_enterprise", "State Enterprise"),
    ("private", "Private"),
    ("other", "Other"),
]

# Progressive (tiered) deduction brackets: (upper_limit, rate)
_TIERED_BRACKETS = [
    (1_000_000.0, 0.10),
    (5_000_000.0, 0.09),
    (10_000_000.0, 0.08),
    (float("inf"), 0.07),
]


def _compute_tiered_deduction(amount):
    """Return progressive tiered deduction for the given base amount.

    Brackets:
      0 – 1,000,000       → 10 %
      1,000,001 – 5,000,000  → 9 %
      5,000,001 – 10,000,000 → 8 %
      > 10,000,000           → 7 %
    """
    total = 0.0
    prev = 0.0
    for cap, rate in _TIERED_BRACKETS:
        if amount <= prev:
            break
        total += (min(amount, cap) - prev) * rate
        prev = cap
    return total


class KrisProject(models.Model):
    _name = "kris.project"
    _description = "KRIS Project"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc"
    _rec_name = "name"

    name = fields.Char(
        string="Project Number",
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
    )
    project_name = fields.Char(
        string="Project Name",
        required=True,
        tracking=True,
    )
    project_category_id = fields.Many2one(
        comodel_name="kris.project.category",
        string="Project Category",
        required=True,
        tracking=True,
    )
    project_type_id = fields.Many2one(
        comodel_name="kris.project.type",
        string="Project Type",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancel", "Cancel"),
        ],
        string="State",
        default="draft",
        readonly=True,
        copy=False,
        tracking=True,
    )
    can_edit = fields.Boolean(
        compute="_compute_can_edit",
    )
    client_name = fields.Char(
        string="Client Name",
        tracking=True,
    )
    client_location = fields.Char(
        string="Client Location",
        tracking=True,
    )
    client_tax_number = fields.Char(
        string="Client Tax Number",
        tracking=True,
    )
    client_org_type = fields.Selection(
        selection=CLIENT_ORG_TYPE_SELECTION,
        string="Client Organization",
        tracking=True,
    )
    manager_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Project Manager",
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Leader Department",
        compute="_compute_department_id",
        store=True,
        readonly=True,
        tracking=True,
    )
    # --- Financial fields ---
    project_value = fields.Monetary(
        string="Project Value",
        tracking=True,
    )
    equipment_cost = fields.Monetary(
        string="Equipment Cost",
        tracking=True,
    )
    operating_expense = fields.Monetary(
        string="Operating Expense",
        tracking=True,
    )
    extra_value = fields.Monetary(
        string="Extra Value",
        tracking=True,
    )
    allocatable_value = fields.Monetary(
        string="Allocatable Value",
        compute="_compute_allocatable_value",
    )
    maintenance_deduction_type = fields.Selection(
        selection=[
            ("tiered", "Tiered"),
            ("custom", "Custom"),
        ],
        string="Maintenance Deduction Type",
        default="tiered",
        required=True,
        tracking=True,
    )
    maintenance_deduction_pct = fields.Float(
        string="% หักค่าบำรุง",
        digits=(5, 2),
        tracking=True,
    )
    maintenance_deduction_amount = fields.Monetary(
        string="Maintenance Deduction",
        compute="_compute_maintenance_deduction_amount",
        store=True,
    )
    # --- Allocation template ---
    allocation_template_id = fields.Many2one(
        comodel_name="kris.project.allocation.template",
        string="แม่แบบการจัดสรร",
    )
    # --- Contract fields ---
    contract_number = fields.Char(
        string="Contract Number",
        tracking=True,
    )
    date_contract_start = fields.Date(
        string="Date Start",
        tracking=True,
    )
    date_contract_end = fields.Date(
        string="Date End",
        tracking=True,
    )
    project_duration = fields.Integer(
        string="Duration (Day)",
        compute="_compute_project_duration",
        store=True,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
    )
    # --- One2many ---
    installment_ids = fields.One2many(
        comodel_name="kris.project.installment",
        inverse_name="project_id",
        string="Installment",
    )
    receipt_ids = fields.One2many(
        comodel_name="kris.project.receipt",
        inverse_name="project_id",
        string="Revenue",
    )
    allocation_line_ids = fields.One2many(
        comodel_name="kris.project.allocation.line",
        inverse_name="project_id",
        string="การจัดสรรรายได้",
    )
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        relation="kris_project_attachment_rel",
        column1="project_id",
        column2="attachment_id",
        string="Attachment",
    )
    # --- Computed totals ---
    total_installment_amount = fields.Monetary(
        string="Total Installment Amount",
        compute="_compute_totals",
        store=True,
    )
    total_received_amount = fields.Monetary(
        string="Total Amount Received",
        compute="_compute_totals",
        store=True,
    )
    total_net_received = fields.Monetary(
        string="Total Net Received",
        compute="_compute_totals",
        store=True,
    )
    revenue_remaining = fields.Monetary(
        string="Revenue Remaining",
        compute="_compute_totals",
        store=True,
    )
    over_revenue = fields.Monetary(
        string="Over Revenue",
        compute="_compute_totals",
        store=True,
    )
    # --- Standard fields ---
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="สกุลเงิน",
        readonly=True,
    )
    note = fields.Text(
        string="Note",
        tracking=True,
    )
    # --- Warning flags ---
    warn_allocation_mismatch = fields.Boolean(
        compute="_compute_warnings",
    )
    warn_installment_maintenance_mismatch = fields.Boolean(
        compute="_compute_warnings",
    )
    warn_installment_total_mismatch = fields.Boolean(
        compute="_compute_warnings",
    )
    warn_extra_overshoot = fields.Boolean(
        compute="_compute_warnings",
    )

    @api.depends(
        "maintenance_deduction_amount",
        "allocation_line_ids.estimated_amount",
        "installment_ids.maintenance_fee",
        "installment_ids.extra_income",
        "total_installment_amount",
        "project_value",
        "extra_value",
    )
    def _compute_warnings(self):
        prec = self.env["decimal.precision"].precision_get("Account")
        for rec in self:
            alloc_total = sum(rec.allocation_line_ids.mapped("estimated_amount"))
            rec.warn_allocation_mismatch = (
                bool(rec.allocation_line_ids)
                and float_compare(
                    alloc_total, rec.maintenance_deduction_amount, precision_digits=prec
                )
                != 0
            )
            if rec.installment_ids:
                maint_total = sum(rec.installment_ids.mapped("maintenance_fee"))
                rec.warn_installment_maintenance_mismatch = (
                    float_compare(
                        maint_total,
                        rec.maintenance_deduction_amount,
                        precision_digits=prec,
                    )
                    != 0
                )
                rec.warn_installment_total_mismatch = (
                    float_compare(
                        rec.total_installment_amount,
                        rec.project_value,
                        precision_digits=prec,
                    )
                    != 0
                )
                extra_total = sum(rec.installment_ids.mapped("extra_income"))
                rec.warn_extra_overshoot = (
                    float_compare(extra_total, rec.extra_value, precision_digits=prec)
                    > 0
                )
            else:
                rec.warn_installment_maintenance_mismatch = False
                rec.warn_installment_total_mismatch = False
                rec.warn_extra_overshoot = False

    @api.depends("state")
    def _compute_can_edit(self):
        for rec in self:
            rec.can_edit = rec.state == "draft"

    @api.depends("operating_expense")
    def _compute_allocatable_value(self):
        for rec in self:
            rec.allocatable_value = rec.operating_expense

    @api.depends(
        "operating_expense",
        "maintenance_deduction_type",
        "maintenance_deduction_pct",
    )
    def _compute_maintenance_deduction_amount(self):
        for rec in self:
            if rec.maintenance_deduction_type == "tiered":
                rec.maintenance_deduction_amount = _compute_tiered_deduction(
                    rec.operating_expense
                )
            else:
                rec.maintenance_deduction_amount = (
                    rec.operating_expense * rec.maintenance_deduction_pct / 100.0
                )

    @api.depends(
        "installment_ids.amount",
        "receipt_ids.amount",
        "receipt_ids.net_amount",
        "project_value",
    )
    def _compute_totals(self):
        for rec in self:
            rec.total_installment_amount = sum(rec.installment_ids.mapped("amount"))
            rec.total_received_amount = sum(rec.receipt_ids.mapped("amount"))
            rec.total_net_received = sum(rec.receipt_ids.mapped("net_amount"))
            diff = rec.project_value - rec.total_received_amount
            rec.revenue_remaining = max(0.0, diff)
            rec.over_revenue = max(0.0, -diff)

    @api.depends("manager_id", "manager_id.department_id")
    def _compute_department_id(self):
        for rec in self:
            rec.department_id = rec.manager_id.department_id

    @api.depends("date_contract_start", "date_contract_end")
    def _compute_project_duration(self):
        for rec in self:
            if rec.date_contract_start and rec.date_contract_end:
                rec.project_duration = max(
                    0, (rec.date_contract_end - rec.date_contract_start).days
                )
            else:
                rec.project_duration = 0

    @api.onchange("project_value", "equipment_cost")
    def _onchange_operating_expense_suggest(self):
        self.operating_expense = self.project_value - self.equipment_cost

    @api.onchange("project_category_id")
    def _onchange_project_category_id(self):
        if (
            self.project_type_id
            and self.project_type_id.category_id != self.project_category_id
        ):
            self.project_type_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("kris.project") or _("New")
                )
        return super().create(vals_list)

    def action_add_receipt(self):
        self.ensure_one()
        return {
            "name": _("Revenue Record"),
            "type": "ir.actions.act_window",
            "res_model": "kris.project.receipt.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_add_installment(self):
        self.ensure_one()
        return {
            "name": _("Add Installment"),
            "type": "ir.actions.act_window",
            "res_model": "kris.project.installment",
            "view_mode": "form",
            "target": "new",
            "context": {"default_project_id": self.id},
        }

    def action_apply_allocation_template(self):
        self.ensure_one()
        if not self.allocation_template_id:
            raise UserError(_("Please select an allocation template first."))
        base_amount = self.maintenance_deduction_amount
        skip_ctx = self.with_context(skip_message_post=True)
        skip_ctx.allocation_line_ids.unlink()
        skip_ctx.allocation_line_ids = [
            (
                0,
                0,
                {
                    "sequence": tl.sequence,
                    "item_id": tl.item_id.id,
                    "estimated_amount": base_amount * tl.allocation_pct / 100.0,
                },
            )
            for tl in self.allocation_template_id.line_ids
        ]
        self.message_post(
            body=_("ใช้แม่แบบการจัดสรร: %s") % self.allocation_template_id.name,
            subtype_xmlid="mail.mt_note",
        )
