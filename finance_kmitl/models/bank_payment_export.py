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
    def _transfer_payment_method(self):
        """The KMITL เงินโอน method — the only one an e-payment file carries."""
        return self.env.ref(
            "account_kmitl.payment_method_transfer_out",
            raise_if_not_found=False,
        )

    def _check_constraint_create_bank_payment_export(self, payments):
        """Replace the base check, which insists on posted manual payments.

        Deliberately does not call super(): KMITL exports *submitted* payments
        on the KMITL transfer method, which the base rejects outright. The
        per-bank rules layered on top would be silenced by that, so they are
        invoked through their own hook.
        """
        self._check_bank_specific_constraint(payments)
        comment_template = payments[0].bank_payment_template_id
        previous_currency = False
        method_transfer_out = self._transfer_payment_method()
        for payment in payments:
            if payment.kmitl_payment_type_id.is_cheque:
                raise UserError(
                    _("Cheque payments cannot be exported to the bank: %s")
                    % payment.name
                )
            if (
                method_transfer_out
                and payment.payment_method_id != method_transfer_out
            ):
                raise UserError(
                    _(
                        "You can export bank payments with the '%s' payment "
                        "method only."
                    )
                    % method_transfer_out.name
                )
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
    # E-payment result confirmation (manual, whole batch)
    # -------------------------------------------------------------------------
    def action_mark_all_epayment_success(self):
        self.mapped("export_line_ids")._apply_epayment_result("success")

    def action_mark_all_epayment_failed(self):
        self.mapped("export_line_ids")._apply_epayment_result("failed")

    # -------------------------------------------------------------------------
    def _domain_payment_id(self):
        """Select submitted KMITL transfer payments (instead of posted Manual
        ones) when pulling every payment into an export batch."""
        domain = super()._domain_payment_id()
        method_transfer_out = self._transfer_payment_method()
        new_domain = []
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and leaf[0] == "state":
                new_domain.append(("state", "=", "submitted"))
            elif (
                isinstance(leaf, (list, tuple))
                and leaf[0] == "payment_method_id"
                and method_transfer_out
            ):
                new_domain.append(
                    ("payment_method_id", "=", method_transfer_out.id)
                )
            else:
                new_domain.append(leaf)
        # Cheques are handed over physically, never sent in an e-payment file.
        new_domain.append(("kmitl_payment_type_id.is_cheque", "=", False))
        return new_domain

