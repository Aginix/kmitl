# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class BankPaymentExport(models.Model):
    _name = "bank.payment.export"
    _inherit = ["bank.payment.export", "sarabun.document.mixin", "thai.date.mixin"]

    state = fields.Selection(
        selection_add=[("submitted", "Submitted"), ("confirm",)],
        ondelete={"submitted": "set default"},
    )
    main_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Main Sarabun Document",
        copy=False,
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

    # -------------------------------------------------------------------------
    # Sarabun integration
    # -------------------------------------------------------------------------
    def _prepare_sarabun_document_vals(self):
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = _("Bank Payment Export: %s") % self.name
        return vals

    def _on_sarabun_completed(self, document):
        _logger.info(
            "Sarabun completed for Bank Payment Export %s (id=%s) from document %s",
            self.name,
            self.id,
            document.name,
        )
        self.action_confirm()
        self.message_post(
            body=_("Approved via Sarabun document: %s") % document.name,
        )

    def _on_sarabun_rejected(self, document, recipient):
        self.state = "draft"
        reason = recipient.comment if recipient else _("No reason provided")
        self.message_post(
            body=_("Rejected via Sarabun. Reason: %s") % reason,
        )

    def _get_sarabun_report_action(self):
        return self.env.ref(
            "account_payment_kmitl.action_report_bank_payment_export"
        )

    def action_submit_to_sarabun(self):
        """Submit bank payment export to Sarabun for approval routing."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Only draft exports can be submitted."))
        self._check_constraint_confirm()
        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))
        self.main_sarabun_document_id = document
        self.state = "submitted"
        self.message_post(
            body=_("Submitted to Sarabun for approval: %s") % document.name,
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    # -------------------------------------------------------------------------
    # Override cancel to also handle submitted state
    # -------------------------------------------------------------------------
    def action_cancel(self):
        """Allow canceling from submitted state as well."""
        for rec in self:
            if rec.state == "submitted":
                rec.state = "cancel"
            else:
                super(BankPaymentExport, rec).action_cancel()
        return True
