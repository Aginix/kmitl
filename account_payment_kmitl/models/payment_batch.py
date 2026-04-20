# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class PaymentBatch(models.Model):
    _name = "payment.batch"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _description = "Payment Batch"
    _order = "date desc, id desc"
    _state_from = ["submitted"]
    _state_to = ["approved"]
    _tier_validation_manual_config = False

    name = fields.Char(
        string="Number",
        readonly=True,
        copy=False,
        default="/",
    )
    description = fields.Char(
        string="Description",
        tracking=True,
    )
    date = fields.Date(
        string="Planned Payment Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        states={"draft": [("readonly", False)]},
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="company_id.currency_id",
    )
    bank_payment_export_ids = fields.One2many(
        comodel_name="bank.payment.export",
        inverse_name="payment_batch_id",
        string="Bank Payment Exports",
        states={"draft": [("readonly", False)]},
        readonly=True,
    )
    total_amount = fields.Monetary(
        string="Total Amount",
        currency_field="currency_id",
        compute="_compute_total_amount",
        store=True,
    )
    export_count = fields.Integer(
        string="Export Count",
        compute="_compute_export_count",
    )
    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        store=True,
        compute="_compute_date_range_fy",
        search="_search_date_range_fy",
    )

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "payment.batch",
                        sequence_date=vals.get("date"),
                    )
                    or "/"
                )
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------
    @api.depends("bank_payment_export_ids.total_amount")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(
                rec.bank_payment_export_ids.mapped("total_amount")
            )

    @api.depends("bank_payment_export_ids")
    def _compute_export_count(self):
        for rec in self:
            rec.export_count = len(rec.bank_payment_export_ids)

    @api.depends("date", "company_id")
    def _compute_date_range_fy(self):
        for rec in self:
            date = fields.Date.to_date(rec.date)
            company = rec.company_id
            rec.account_fiscal_year_id = (
                company and date and company.find_daterange_fy(date) or False
            )

    @api.model
    def _search_date_range_fy(self, operator, value):
        if operator in ("=", "!=", "in", "not in"):
            date_range_domain = [("id", operator, value)]
        else:
            date_range_domain = [("name", operator, value)]
        date_ranges = self.env["account.fiscal.year"].search(date_range_domain)
        domain = [("id", "=", -1)]
        for date_range in date_ranges:
            domain = expression.OR(
                [
                    domain,
                    [
                        "&",
                        ("date", ">=", date_range.date_from),
                        ("date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain

    # -------------------------------------------------------------------------
    # Workflow actions
    # -------------------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if not rec.bank_payment_export_ids:
                raise UserError(
                    _("Cannot submit an empty payment batch. "
                      "Please add at least one bank payment export.")
                )
            rec.write({"state": "submitted"})
            if rec.need_validation:
                rec.request_validation()

    def action_approve(self):
        for rec in self:
            rec.write({"state": "approved"})
            exports_to_confirm = rec.bank_payment_export_ids.filtered(
                lambda e: e.state == "draft"
            )
            exports_to_confirm.action_confirm()

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        for rec in self:
            done_exports = rec.bank_payment_export_ids.filtered(
                lambda e: e.state == "done"
            )
            if done_exports:
                raise UserError(
                    _(
                        "Cannot cancel this payment batch because some "
                        "bank payment exports have already been exported."
                    )
                )
            active_exports = rec.bank_payment_export_ids.filtered(
                lambda e: e.state != "cancel"
            )
            active_exports.action_cancel()
            rec.write({"state": "cancel"})
            if rec.need_validation:
                rec.restart_validation()

    def action_draft(self):
        for rec in self:
            if rec.state not in ("cancel", "submitted"):
                raise UserError(
                    _("Only cancelled or submitted batches can be reset to draft.")
                )
            rec.write({"state": "draft"})
            if rec.need_validation:
                rec.restart_validation()

    def _check_auto_done(self):
        """Called from bank.payment.export when it reaches done state."""
        for rec in self:
            if rec.state != "approved":
                continue
            if all(e.state == "done" for e in rec.bank_payment_export_ids):
                rec.action_done()

    # -------------------------------------------------------------------------
    # Tier validation
    # -------------------------------------------------------------------------
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res += ["message_follower_ids", "message_ids"]
        return res
