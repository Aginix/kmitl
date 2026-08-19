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
    paying_account_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Paying Account",
        domain="[('payment_type', '=', 'outbound'), "
        "('payment_method_id.code', '=', 'kmitl_transfer'), "
        "('bank_account_id', '!=', False)]",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
        help="The account this file debits. One file is uploaded to one bank "
        "and debits one account, so it is chosen first and the payments that "
        "can be picked into the file are narrowed to the ones paid from it.",
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

    def _check_single_paying_account(self, payments):
        """One file is uploaded to one bank and debits one account.

        Checked against the payments rather than against the header field, so it
        holds however the batch was assembled — picking payments by hand,
        pulling every submitted one, or opening the export from a selection.
        """
        paying_accounts = payments.mapped("payment_method_line_id")
        if len(paying_accounts) > 1:
            raise UserError(
                _(
                    "One file debits one account, but these payments are paid "
                    "from %s. Export them separately, one paying account at a "
                    "time."
                )
                % ", ".join(paying_accounts.mapped("display_name"))
            )
        if paying_accounts and not paying_accounts.bank_account_id:
            raise UserError(
                _(
                    "%s names no bank account, so the file would carry no "
                    "sending account. Set it in Finance ▸ Settings ▸ Paying "
                    "Accounts."
                )
                % paying_accounts.display_name
            )
        return True

    def _check_constraint_confirm(self):
        """Also guard the batches assembled by pulling every submitted payment,
        which never pass through the create-from-selection check."""
        res = super()._check_constraint_confirm()
        for record in self:
            record._check_single_paying_account(
                record.export_line_ids.mapped("payment_id")
            )
        return res

    def _check_constraint_create_bank_payment_export(self, payments):
        """Replace the base check, which insists on posted Manual payments.

        Deliberately does not call super(): a KMITL file carries vouchers the
        *finance* office has confirmed for the bank and the accounting office has
        not booked yet, which the base rejects outright — it expects the entry to
        be posted first. The per-bank rules layered on top would be silenced by
        that, so they are invoked through their own hook.
        """
        self._check_bank_specific_constraint(payments)
        self._check_single_paying_account(payments)
        comment_template = payments[0].bank_payment_template_id
        previous_currency = False
        method_transfer_out = self._transfer_payment_method()
        for payment in payments:
            if not payment.needs_bank_export:
                raise UserError(
                    _(
                        "%s is settled outside the bank file (cheque or cash) "
                        "and cannot be exported."
                    )
                    % payment.name
                )
            if method_transfer_out and payment.payment_method_id != method_transfer_out:
                raise UserError(
                    _("You can export bank payments with the '%s' payment method only.")
                    % method_transfer_out.name
                )
            if payment.bank_payment_template_id != comment_template:
                raise UserError(
                    _("All payments must have the same bank payment template.")
                )
            if payment.export_status != "draft":
                raise UserError(_("Payments have been already exported."))
            if payment.finance_state != "confirmed":
                raise UserError(
                    _(
                        "%s is not confirmed for the bank, so it may still change "
                        "and cannot be put in a file."
                    )
                    % payment.display_name
                )
            if previous_currency and payment.currency_id != previous_currency:
                raise UserError(_("You can export bank payments with 1 currency only."))
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
        """Select the KMITL transfer vouchers the finance office has confirmed for
        the bank (instead of posted Manual ones) when pulling every payment into an
        export batch. The accounting office has not booked them yet — their own
        status is still draft, which is why the base's ``state`` leaf is replaced
        rather than narrowed."""
        domain = super()._domain_payment_id()
        method_transfer_out = self._transfer_payment_method()
        new_domain = []
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and leaf[0] == "state":
                new_domain.append(("finance_state", "=", "confirmed"))
            elif (
                isinstance(leaf, (list, tuple))
                and leaf[0] == "payment_method_id"
                and method_transfer_out
            ):
                new_domain.append(("payment_method_id", "=", method_transfer_out.id))
            else:
                new_domain.append(leaf)
        # One file debits one account. Narrowing here is what keeps two paying
        # accounts out of the same batch in the first place, rather than only
        # rejecting the mix afterwards.
        if len(self) == 1 and self.paying_account_id:
            new_domain.append(
                ("payment_method_line_id", "=", self.paying_account_id.id)
            )
        return new_domain

    def _get_context_create_bank_payment_export(self, payments):
        """Take the file's bank and paying account from the payments.

        The base derives the bank from the payment journal's bank account, which
        is empty at KMITL — a journal is a voucher type (ใบสำคัญ) and holds no
        bank. The paying account is where that lives now.
        """
        ctx = super()._get_context_create_bank_payment_export(payments)
        paying_accounts = payments.mapped("payment_method_line_id")
        if len(paying_accounts) == 1:
            ctx["default_paying_account_id"] = paying_accounts.id
            if paying_accounts.bank_id.bic:
                ctx["default_bank"] = paying_accounts.bank_id.bic
        return ctx
