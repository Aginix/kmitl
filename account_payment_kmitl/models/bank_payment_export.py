# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class BankPaymentExport(models.Model):
    _name = "bank.payment.export"
    _inherit = ["bank.payment.export", "thai.date.mixin"]

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        store=True,
        compute="_compute_date_range_fy",
        search="_search_date_range_fy",
    )

    # -------------------------------------------------------------------------
    # Fiscal year
    # -------------------------------------------------------------------------
    @api.depends("effective_date", "company_id")
    def _compute_date_range_fy(self):
        for rec in self:
            date = fields.Date.to_date(rec.effective_date)
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
                        ("effective_date", ">=", date_range.date_from),
                        ("effective_date", "<=", date_range.date_to),
                        "|",
                        ("company_id", "=", False),
                        ("company_id", "=", date_range.company_id.id),
                    ],
                ]
            )
        return domain

    # -------------------------------------------------------------------------
    # Overrides: accept submitted payments instead of posted
    # -------------------------------------------------------------------------
    def _check_constraint_create_bank_payment_export(self, payments):
        """Override to accept submitted payments instead of posted."""
        comment_template = payments[0].bank_payment_template_id
        previous_currency = False
        for payment in payments:
            if payment.bank_payment_template_id != comment_template:
                raise UserError(
                    _("All payments must have the same bank payment template.")
                )
            if payment.export_status != "draft":
                raise UserError(_("Payments have been already exported."))
            if payment.state != "submitted":
                raise UserError(
                    _("You can export bank payments state 'submitted' only")
                )
            if previous_currency and payment.currency_id != previous_currency:
                raise UserError(
                    _("You can export bank payments with 1 currency only.")
                )
            previous_currency = payment.currency_id

    # -------------------------------------------------------------------------
    def _domain_payment_id(self):
        domain = super()._domain_payment_id()
        # Replace ("state", "=", "posted") with ("state", "=", "submitted")
        new_domain = []
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and leaf[0] == "state":
                new_domain.append(("state", "=", "submitted"))
            else:
                new_domain.append(leaf)
        return new_domain

