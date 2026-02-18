# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class KrisProject(models.Model):
    _name = "kris.project"
    _description = "KRIS Research Project"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name desc, id desc"

    READONLY_STATES = {
        "active": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }

    name = fields.Char(
        string="Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
    )
    project_name = fields.Char(
        string="Project Name",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    description = fields.Text(
        string="Description",
        states=READONLY_STATES,
    )
    researcher_id = fields.Many2one(
        comodel_name="res.partner",
        string="Principal Investigator",
        tracking=True,
        states=READONLY_STATES,
    )
    funding_organization_id = fields.Many2one(
        comodel_name="res.partner",
        string="Funding Organization",
        tracking=True,
        states=READONLY_STATES,
    )
    grant_amount = fields.Monetary(
        string="Grant Amount",
        currency_field="currency_id",
        tracking=True,
        states=READONLY_STATES,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        states=READONLY_STATES,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        states=READONLY_STATES,
    )
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Home Department",
        domain=[("root_plan_id.code", "=", "departments")],
        tracking=True,
        states=READONLY_STATES,
    )
    allocation_config_id = fields.Many2one(
        comodel_name="kris.allocation.config",
        string="Default Allocation Config",
        tracking=True,
        states=READONLY_STATES,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        states=READONLY_STATES,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        tracking=True,
        states=READONLY_STATES,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )
    funding_receipt_ids = fields.One2many(
        comodel_name="kris.funding.receipt",
        inverse_name="project_id",
        string="Funding Receipts",
        readonly=True,
    )
    total_received = fields.Monetary(
        string="Total Received",
        currency_field="currency_id",
        compute="_compute_total_received",
        store=True,
    )
    receipt_count = fields.Integer(
        string="Receipt Count",
        compute="_compute_receipt_count",
    )

    @api.depends("funding_receipt_ids.amount", "funding_receipt_ids.state")
    def _compute_total_received(self):
        for project in self:
            posted_receipts = project.funding_receipt_ids.filtered(
                lambda r: r.state == "posted"
            )
            project.total_received = sum(posted_receipts.mapped("amount"))

    def _compute_receipt_count(self):
        for project in self:
            project.receipt_count = len(project.funding_receipt_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("kris.project") or "/"
                )
        return super().create(vals_list)

    def action_activate(self):
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft projects can be activated."))
            record.state = "active"

    def action_done(self):
        for record in self:
            if record.state != "active":
                raise UserError(_("Only active projects can be marked as done."))
            record.state = "done"

    def action_cancel(self):
        for record in self:
            if record.state in ("done",):
                raise UserError(_("Done projects cannot be cancelled."))
            record.state = "cancel"

    def action_draft(self):
        for record in self:
            if record.state not in ("cancel",):
                raise UserError(_("Only cancelled projects can be reset to draft."))
            record.state = "draft"

    def action_view_receipts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Funding Receipts"),
            "res_model": "kris.funding.receipt",
            "view_mode": "tree,form",
            "domain": [("project_id", "=", self.id)],
            "context": {"default_project_id": self.id},
        }
