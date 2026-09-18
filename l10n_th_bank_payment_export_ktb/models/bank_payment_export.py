# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BankPaymentExport(models.Model):
    _inherit = "bank.payment.export"

    bank = fields.Selection(
        selection_add=[("KRTHTHBK", "KTB")],
        ondelete={"KRTHTHBK": "cascade"},
    )
    # Configuration
    ktb_company_id = fields.Char(
        string="KTB Company ID",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ktb_sender_name = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    # filter
    ktb_is_editable = fields.Boolean(
        compute="_compute_ktb_editable",
        string="KTB Editable",
    )
    ktb_bank_type = fields.Selection(
        selection=[
            ("standard", "Standard / Express"),
            ("direct", "Direct"),
        ],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ktb_service_type_standard = fields.Selection(
        selection=[
            ("01", "01 - Salary, Wages, Gratuity, Pension"),
            ("02", "02 - Dividend"),
            ("03", "03 - Interest"),
            ("04", "04 - Goods and Services"),
            ("05", "05 - Sale of Securities"),
            ("06", "06 - Tax Refund"),
            ("07", "07 - Loan"),
            ("59", "59 - Other"),
        ],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    ktb_service_type_direct = fields.Selection(
        selection=[
            ("02", "02 - Salary Deposit"),
            ("04", "04 - Bond Interest Payment"),
            ("09", "09 - Insurance Premium Payment"),
            ("10", "10 - Telephone Payment"),
            ("11", "11 - Electricity Payment"),
            ("12", "12 - Water Payment"),
            ("14", "14 - Purchase & Service Payment"),
            ("15", "15 - Government Savings Bank (GSB) Payment"),
            ("21", "21 - Securities Payment"),
            ("25", "25 - Clearing Bank Payment"),
            ("27", "27 - Social Security Office (SSO) Payment"),
            ("28", "28 - Government Lottery Office Payment"),
            ("37", "37 - Electronic Card Payment"),
            ("46", "46 - Pension Fund Payment"),
        ],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.onchange("ktb_bank_type")
    def _onchange_ktb_bank_type(self):
        if self.ktb_bank_type == "standard":
            self.ktb_service_type_direct = False
        else:
            self.ktb_service_type_standard = False

    @api.depends("bank")
    def _compute_required_effective_date(self):
        res = super()._compute_required_effective_date()
        for rec in self.filtered(lambda l: l.bank == "KRTHTHBK"):
            rec.is_required_effective_date = True
        return res

    @api.depends("bank")
    def _compute_ktb_editable(self):
        for export in self:
            export.ktb_is_editable = True if export.bank == "KRTHTHBK" else False

    def _check_constraint_confirm(self):
        res = super()._check_constraint_confirm()
        for rec in self.filtered(lambda l: l.bank == "KRTHTHBK"):
            if not rec.ktb_bank_type:
                raise UserError(_("You need to add 'Bank Type' before confirm."))
            if rec.ktb_bank_type == "direct" and any(
                line.payment_bank_id.bic != rec.bank for line in rec.export_line_ids
            ):
                raise UserError(
                    _("Bank type '{}' can not export payment to other bank.").format(
                        dict(self._fields["ktb_bank_type"].selection).get(
                            self.ktb_bank_type
                        )
                    )
                )
            if rec.ktb_bank_type == "standard" and any(
                line.payment_bank_id.bic == rec.bank for line in rec.export_line_ids
            ):
                raise UserError(
                    _("Bank type '{}' can not export payment to the same bank.").format(
                        dict(self._fields["ktb_bank_type"].selection).get(
                            self.ktb_bank_type
                        )
                    )
                )
        return res

    def _get_context_create_bank_payment_export(self, payments):
        ctx = super()._get_context_create_bank_payment_export(payments)
        partner_bic_bank = list(set(payments.mapped("partner_bank_id.bank_id.bic")))
        # KTB Bank
        if partner_bic_bank and ctx["default_bank"] == "KRTHTHBK":
            # Same bank
            if len(partner_bic_bank) == 1 and partner_bic_bank[0] == "KRTHTHBK":
                ctx.update({"default_ktb_bank_type": "direct"})
            # Other bank
            elif "KRTHTHBK" not in partner_bic_bank:
                ctx.update({"default_ktb_bank_type": "standard"})
        return ctx

    def _check_constraint_line(self):
        # Add condition with line on this function
        res = super()._check_constraint_line()
        self.ensure_one()
        if self.bank == "KRTHTHBK":
            for line in self.export_line_ids:
                if not line.payment_partner_bank_id:
                    raise UserError(
                        _("Recipient Bank with {} is not selected.").format(
                            line.payment_id.name
                        )
                    )
        return res

    def _check_constraint_create_bank_payment_export(self, payments):
        res = super()._check_constraint_create_bank_payment_export(payments)
        self._check_bank_specific_constraint(payments)
        return res

    def _check_bank_specific_constraint(self, payments):
        """KTB's own rules on a batch.

        Held in the hook rather than inline above so that a localisation which
        replaces the generic check outright still runs them.
        """
        res = super()._check_bank_specific_constraint(payments)
        payment_bic_bank = list(set(payments.mapped("journal_id.bank_id.bic")))
        payment_bank = len(payment_bic_bank) == 1 and payment_bic_bank[0] or ""
        # Check case KTB must have 1 journal / 1 PE
        if payment_bank == "KRTHTHBK" and len(payments.mapped("journal_id")) > 1:
            raise UserError(
                _("KTB can create bank payment export 1 Journal / 1 Payment Export.")
            )
        for payment in payments:
            # Which outbound payment method may be exported is a company
            # policy, enforced by the module that owns the methods (the base
            # domain and finance_kmitl); here we only require a bank journal.
            if payment.journal_id.type != "bank":
                raise UserError(
                    _("You can export bank payments with journal 'Bank' only")
                )
            if payment.company_id.currency_id != payment.currency_id:
                raise UserError(
                    _("Payments must be currency '{}' only").format(
                        payment.company_id.currency_id.name
                    )
                )
        return res
