import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

CLIENT_ORG_TYPE_SELECTION = [
    ("government", "Government Agency"),
    ("state_enterprise", "State Enterprise"),
    ("public_organization", "Public Organization"),
    ("independent_organization", "Independent Organization"),
    ("private", "Private Company"),
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
    _inherit = ["mail.thread", "mail.activity.mixin", "base.exception"]
    _order = "main_exception_id asc, name desc"
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
            ("suspended", "Suspended"),
            ("done", "Done"),
            ("terminated", "Terminated"),
            ("conditional_close", "Closed with Conditions"),
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
    no_installment_tracking = fields.Boolean(
        string="ไม่มีงวดงานกำกับ",
        tracking=True,
        help="ติ๊กเมื่อโครงการนี้ไม่มีงวดงานกำกับ: ข้ามการตรวจสอบงวดงานตอนยืนยัน "
        "แก้ไขงวดงานได้ระหว่างดำเนินการ และปิดโครงการได้โดยไม่ต้องรับเงินครบ",
    )
    installment_editable = fields.Boolean(
        compute="_compute_installment_editable",
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
        compute="_compute_operating_expense",
        store=True,
        readonly=False,
        tracking=True,
    )
    extra_value = fields.Monetary(
        string="Extra Value",
        tracking=True,
    )
    extra_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Extra Payee",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
    allocatable_value = fields.Monetary(
        string="Allocatable Value",
        compute="_compute_allocatable_value",
    )
    maintenance_deduction_type = fields.Selection(
        selection=[
            ("tiered", "Tiered"),
            ("custom", "Custom %"),
            ("fixed", "Fixed Amount"),
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
    maintenance_deduction_fixed_amount = fields.Monetary(
        string="จำนวนเงินค่าบำรุง",
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
    project_code = fields.Char(
        string="Project Code",
        tracking=True,
    )
    contract_number = fields.Char(
        string="Employer Contract Number",
        tracking=True,
    )
    kris_contract_date = fields.Date(
        string="Contract/MOU Date",
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
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
    )
    # --- One2many ---
    installment_ids = fields.One2many(
        comodel_name="kris.project.installment",
        inverse_name="project_id",
        string="Installment",
        copy=True,
    )
    receipt_ids = fields.One2many(
        comodel_name="kris.project.receipt",
        inverse_name="project_id",
        string="Revenue",
        copy=False,
    )
    allocation_line_ids = fields.One2many(
        comodel_name="kris.project.allocation.line",
        inverse_name="project_id",
        string="การจัดสรรรายได้",
        copy=True,
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
    total_extra_received = fields.Monetary(
        string="Total Extra Received",
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
    warn_cancel_with_receipts = fields.Boolean(
        compute="_compute_warnings",
    )
    warn_maintenance_exceeds_expense = fields.Boolean(
        compute="_compute_warnings",
    )

    @api.depends(
        "maintenance_deduction_amount",
        "operating_expense",
        "allocation_line_ids.estimated_amount",
        "installment_ids.maintenance_fee",
        "installment_ids.extra_income",
        "total_installment_amount",
        "project_value",
        "extra_value",
        "no_installment_tracking",
        "state",
        "receipt_ids",
    )
    def _compute_warnings(self):
        prec = self.env["decimal.precision"].precision_get("Account")
        for rec in self:
            rec.warn_cancel_with_receipts = bool(rec.receipt_ids) and rec.state in (
                "draft",
                "in_progress",
            )
            rec.warn_maintenance_exceeds_expense = (
                float_compare(
                    rec.maintenance_deduction_amount,
                    rec.operating_expense,
                    precision_digits=prec,
                )
                > 0
            )
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
                    not rec.no_installment_tracking
                    and float_compare(
                        maint_total,
                        rec.maintenance_deduction_amount,
                        precision_digits=prec,
                    )
                    != 0
                )
                rec.warn_installment_total_mismatch = (
                    not rec.no_installment_tracking
                    and float_compare(
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

    @api.depends("state", "no_installment_tracking")
    def _compute_installment_editable(self):
        # Installments remain editable after confirmation only for projects
        # flagged as having no work-period tracking; otherwise draft-only.
        for rec in self:
            rec.installment_editable = rec.state == "draft" or (
                rec.state == "in_progress" and rec.no_installment_tracking
            )

    @api.depends("operating_expense")
    def _compute_allocatable_value(self):
        for rec in self:
            rec.allocatable_value = rec.operating_expense

    @api.depends(
        "operating_expense",
        "maintenance_deduction_type",
        "maintenance_deduction_pct",
        "maintenance_deduction_fixed_amount",
    )
    def _compute_maintenance_deduction_amount(self):
        for rec in self:
            if rec.maintenance_deduction_type == "tiered":
                rec.maintenance_deduction_amount = _compute_tiered_deduction(
                    rec.operating_expense
                )
            elif rec.maintenance_deduction_type == "custom":
                rec.maintenance_deduction_amount = (
                    rec.operating_expense * rec.maintenance_deduction_pct / 100.0
                )
            else:  # "fixed"
                rec.maintenance_deduction_amount = (
                    rec.maintenance_deduction_fixed_amount
                )

    @api.depends(
        "installment_ids.received_from_employer",
        "receipt_ids.amount",
        "receipt_ids.net_amount",
        "receipt_ids.extra_income",
        "project_value",
    )
    def _compute_totals(self):
        for rec in self:
            rec.total_installment_amount = sum(rec.installment_ids.mapped("received_from_employer"))
            rec.total_received_amount = sum(rec.receipt_ids.mapped("amount"))
            rec.total_net_received = sum(rec.receipt_ids.mapped("net_amount"))
            rec.total_extra_received = sum(rec.receipt_ids.mapped("extra_income"))
            diff = rec.project_value - rec.total_received_amount
            rec.revenue_remaining = max(0.0, diff)
            rec.over_revenue = max(0.0, -diff)

    @api.depends("date_contract_start", "date_contract_end")
    def _compute_project_duration(self):
        for rec in self:
            if rec.date_contract_start and rec.date_contract_end:
                rec.project_duration = (
                    rec.date_contract_end - rec.date_contract_start
                ).days + 1
            else:
                rec.project_duration = 0

    @api.depends("project_value", "equipment_cost")
    def _compute_operating_expense(self):
        for rec in self:
            rec.operating_expense = rec.project_value - rec.equipment_cost

    @api.onchange("project_category_id")
    def _onchange_project_category_id(self):
        if (
            self.project_type_id
            and self.project_type_id.category_id != self.project_category_id
        ):
            self.project_type_id = False

    @api.onchange("maintenance_deduction_type")
    def _onchange_maintenance_deduction_type(self):
        # Clear the inputs that do not apply to the selected method so stale
        # values are neither stored nor exported (mirrors the Odoo core
        # pattern in product.pricelist.item._onchange_compute_price).
        if self.maintenance_deduction_type != "custom":
            self.maintenance_deduction_pct = 0.0
        if self.maintenance_deduction_type != "fixed":
            self.maintenance_deduction_fixed_amount = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("kris.project") or _("New")
                )
        return super().create(vals_list)

    @api.returns("self", lambda value: value.id)
    def copy(self, default=None):
        # Duplicate carries over the allocation (การจัดสรร) and installments
        # (งวดงาน) but never the revenue (รายรับ); revenue One2many fields are
        # flagged copy=False so the new project starts empty.
        self.ensure_one()
        default = dict(default or {})
        # Append a "(copy)" suffix to the project name only when it would clash
        # with an existing one (a duplicate always clashes with its source).
        if "project_name" not in default and self.project_name:
            if self.search_count([("project_name", "=", self.project_name)]):
                default["project_name"] = _("%s (copy)") % self.project_name
        new = super().copy(default)
        self._copy_installment_allocations(new)
        return new

    def _copy_installment_allocations(self, new):
        """Rebuild the per-installment maintenance breakdown on the copy.

        ``installment_ids`` and ``allocation_line_ids`` are copied via
        ``copy=True``, but ``kris.project.installment.allocation`` cross-links
        both, so each entry's ``allocation_line_id`` must be re-pointed from the
        source lines to the newly created ones. Copy preserves recordset order,
        so the source and new collections align positionally.
        """
        line_map = dict(zip(self.allocation_line_ids, new.allocation_line_ids))
        vals_list = []
        for src_inst, new_inst in zip(self.installment_ids, new.installment_ids):
            for breakdown in src_inst.allocation_ids:
                new_line = line_map.get(breakdown.allocation_line_id)
                if not new_line:
                    continue
                vals_list.append(
                    {
                        "installment_id": new_inst.id,
                        "allocation_line_id": new_line.id,
                        "amount": breakdown.amount,
                    }
                )
        if vals_list:
            self.env["kris.project.installment.allocation"].create(vals_list)

    @api.model
    def _reverse_field(self):
        return "kris_project_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "kris_project.action_kris_project_exception_confirm"
        )

    def _popup_exceptions(self):
        action = super()._popup_exceptions()
        action["context"]["kris_exception_action"] = self.env.context.get(
            "kris_exception_action", "action_confirm"
        )
        return action

    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Only projects that are in draft status can be confirmed.")
                )
        if self.detect_exceptions() and not self.ignore_exception:
            return self.with_context(
                kris_exception_action="action_confirm"
            )._popup_exceptions()
        self.write({"state": "in_progress", "ignore_exception": False})

    def action_cancel(self):
        self.write({"state": "cancel", "ignore_exception": False})

    def action_draft(self):
        allowed = (
            "cancel",
            "in_progress",
            "done",
            "terminated",
            "conditional_close",
        )
        for rec in self:
            if rec.state not in allowed:
                raise UserError(
                    _("This project cannot be reset to draft from its current state.")
                )
        self.write({
            "state": "draft",
            "exception_ids": [(5,)],
            "main_exception_id": False,
            "ignore_exception": False,
        })

    def action_add_receipt(self):
        self.ensure_one()
        if self.state in ("done", "cancel"):
            raise UserError(
                _("Cannot record revenue on a project that is done or cancelled.")
            )
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
        if not self.installment_editable:
            raise UserError(
                _(
                    "Installments can only be edited while the project is in "
                    "draft, or in progress when it has no work-period tracking."
                )
            )
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
        if not self.can_edit:
            raise UserError(
                _("Allocation can only be changed while the project is in draft.")
            )
        if not self.allocation_template_id:
            raise UserError(_("Please select an allocation template first."))
        base_amount = self.maintenance_deduction_amount
        self.allocation_line_ids.unlink()
        self.allocation_line_ids = [
            (
                0,
                0,
                {
                    "sequence": tl.sequence,
                    "item_id": tl.item_id.id,
                    "estimated_amount": base_amount * tl.allocation_pct / 100.0,
                    "department_analytic_id": tl.department_analytic_id.id,
                    "is_locked": tl.is_locked,
                },
            )
            for tl in self.allocation_template_id.line_ids
        ]
