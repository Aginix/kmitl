# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class KrisFundingReceipt(models.Model):
    _name = "kris.funding.receipt"
    _description = "KRIS Funding Receipt"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"

    READONLY_STATES = {
        "confirmed": [("readonly", True)],
        "posted": [("readonly", True)],
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
    ref = fields.Char(
        string="External Reference",
        help="Bankbook entry reference",
        tracking=True,
        states=READONLY_STATES,
    )
    date = fields.Date(
        string="Receipt Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        states=READONLY_STATES,
    )
    project_id = fields.Many2one(
        comodel_name="kris.project",
        string="Research Project",
        required=True,
        domain=[("state", "=", "active")],
        tracking=True,
        states=READONLY_STATES,
    )
    researcher_id = fields.Many2one(
        comodel_name="res.partner",
        string="Principal Investigator",
        related="project_id.researcher_id",
        store=True,
    )
    funding_organization_id = fields.Many2one(
        comodel_name="res.partner",
        string="Funding Organization",
        related="project_id.funding_organization_id",
        store=True,
    )
    department_analytic_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Home Department",
        related="project_id.department_analytic_id",
        store=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        required=True,
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
    allocation_config_id = fields.Many2one(
        comodel_name="kris.allocation.config",
        string="Allocation Configuration",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        domain=[("type", "in", ["bank", "general"])],
        tracking=True,
        states=READONLY_STATES,
    )
    bank_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Bank/Debit Account",
        required=True,
        help="GL account to debit (bank or cash account)",
        tracking=True,
        states=READONLY_STATES,
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        readonly=True,
        copy=False,
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        compute="_compute_account_fiscal_year_id",
        store=True,
        search="_search_account_fiscal_year_id",
    )
    confirmed_by = fields.Many2one(
        comodel_name="res.users",
        string="Confirmed By",
        readonly=True,
        copy=False,
    )
    confirmed_date = fields.Datetime(
        string="Confirmed On",
        readonly=True,
        copy=False,
    )
    posted_by = fields.Many2one(
        comodel_name="res.users",
        string="Posted By",
        readonly=True,
        copy=False,
    )
    posted_date = fields.Datetime(
        string="Posted On",
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("posted", "Posted"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )
    note = fields.Text(string="Notes")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="project_id.company_id",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------
    @api.onchange("project_id")
    def _onchange_project_id(self):
        if self.project_id and self.project_id.allocation_config_id:
            self.allocation_config_id = self.project_id.allocation_config_id

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------
    @api.depends("date", "company_id")
    def _compute_account_fiscal_year_id(self):
        for rec in self:
            date = fields.Date.to_date(rec.date)
            company = rec.company_id or self.env.company
            rec.account_fiscal_year_id = (
                company.find_daterange_fy(date) if date and company else False
            )

    @api.model
    def _search_account_fiscal_year_id(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]

        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)
        domain = [("id", "=", -1)]
        for dr in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("date", ">=", dr.date_from),
                        ("date", "<=", dr.date_to),
                    ],
                ]
            )
        return domain

    # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("kris.funding.receipt") or "/"
                )
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Workflow actions
    # -------------------------------------------------------------------------
    def action_confirm(self):
        """Finance officer confirms receipt after verifying bankbook."""
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only draft receipts can be confirmed."))
            record.confirmed_by = self.env.user
            record.confirmed_date = fields.Datetime.now()
            record.state = "confirmed"

    def action_post(self):
        """Manager posts receipt to journal, creating accounting entry."""
        for record in self:
            if record.state != "confirmed":
                raise UserError(_("Only confirmed receipts can be posted."))
            record._create_account_move()
            record.posted_by = self.env.user
            record.posted_date = fields.Datetime.now()
            record.state = "posted"

    def action_cancel(self):
        """Cancel receipt. Posted receipts must be reversed via JE first."""
        for record in self:
            if record.state == "posted":
                raise UserError(
                    _(
                        "Posted receipts cannot be cancelled directly. "
                        "Please reverse the journal entry first."
                    )
                )
            if record.state == "cancel":
                raise UserError(_("Receipt is already cancelled."))
            record.state = "cancel"

    def action_draft(self):
        """Reset confirmed or cancelled receipt back to draft."""
        for record in self:
            if record.state not in ("confirmed", "cancel"):
                raise UserError(
                    _("Only confirmed or cancelled receipts can be reset to draft.")
                )
            record.confirmed_by = False
            record.confirmed_date = False
            record.state = "draft"

    def action_view_move(self):
        """Open the linked journal entry."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Entry"),
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # -------------------------------------------------------------------------
    # Accounting
    # -------------------------------------------------------------------------
    def _create_account_move(self):
        """
        Create journal entry splitting the receipt amount per allocation config.

        Dr  Bank Account      (full amount)
          Cr  Income Account 1  (line 1 %)
          Cr  Income Account 2  (line 2 %, uses project home dept if is_home_department)
          ...
        Rounding remainder goes to the last credit line.
        """
        self.ensure_one()
        config = self.allocation_config_id
        if not config or not config.line_ids:
            raise UserError(_("Allocation configuration has no lines."))

        lines_sorted = config.line_ids.sorted("sequence")
        total = self.amount
        currency = self.currency_id
        company_currency = self.company_id.currency_id

        move_lines = []

        # Debit line: bank / cash account
        move_lines.append(
            Command.create(
                {
                    "name": self.name,
                    "account_id": self.bank_account_id.id,
                    "debit": total,
                    "credit": 0.0,
                    "currency_id": currency.id if currency != company_currency else False,
                }
            )
        )

        # Credit lines: income accounts per allocation
        computed = []
        running_total = 0.0
        for idx, line in enumerate(lines_sorted):
            is_last = idx == len(lines_sorted) - 1
            if is_last:
                # Remainder to avoid rounding drift
                line_amount = total - running_total
            else:
                line_amount = currency.round(total * line.percentage / 100.0)
                running_total += line_amount

            # Determine which department analytic to use
            if line.is_home_department:
                dept_analytic = self.department_analytic_id
            else:
                dept_analytic = line.department_analytic_id

            analytic_distribution = (
                {str(dept_analytic.id): 100} if dept_analytic else {}
            )

            computed.append(
                {
                    "name": line.name,
                    "account_id": line.account_id.id,
                    "debit": 0.0,
                    "credit": line_amount,
                    "currency_id": currency.id if currency != company_currency else False,
                    "analytic_distribution": analytic_distribution or False,
                }
            )

        for line_vals in computed:
            move_lines.append(Command.create(line_vals))

        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "ref": self.name,
                "date": self.date,
                "journal_id": self.journal_id.id,
                "company_id": self.company_id.id,
                "currency_id": currency.id,
                "line_ids": move_lines,
            }
        )
        move.action_post()
        self.move_id = move
