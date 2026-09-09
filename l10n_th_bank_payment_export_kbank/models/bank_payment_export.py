# Copyright 2024 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number


class BankPaymentExport(models.Model):
    _inherit = "bank.payment.export"

    bank = fields.Selection(
        selection_add=[("KASITHBK", "KBANK")],
        ondelete={"KASITHBK": "cascade"},
    )
    # Configuration
    kbank_company_id = fields.Char(
        string="KBANK Originator Code",
        size=7,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        help="7-digit KBANK originator code (Company/Originator ID) printed in "
        "each detail and the trailer record. Zero-padded to 7 digits on export. "
        "TODO: confirm the exact source/meaning against the official K-Cash "
        "Connect Plus file-format specification.",
    )
    kbank_sender_name = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    kbank_service_type = fields.Selection(
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
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    # filter
    kbank_is_editable = fields.Boolean(
        compute="_compute_kbank_editable",
        string="KBANK Editable",
    )

    @api.depends("bank")
    def _compute_required_effective_date(self):
        res = super()._compute_required_effective_date()
        for rec in self.filtered(lambda l: l.bank == "KASITHBK"):
            rec.is_required_effective_date = True
        return res

    @api.depends("bank")
    def _compute_kbank_editable(self):
        for export in self:
            export.kbank_is_editable = export.bank == "KASITHBK"

    def _check_constraint_line(self):
        res = super()._check_constraint_line()
        self.ensure_one()
        if self.bank == "KASITHBK":
            for line in self.export_line_ids:
                if not line.payment_partner_bank_id:
                    raise UserError(
                        _("Recipient Bank with %(payment)s is not selected.")
                        % {"payment": line.payment_id.name}
                    )
        return res

    def _check_constraint_confirm(self):
        res = super()._check_constraint_confirm()
        # KBANK K-Cash Connect Plus (direct credit) requires a 10-digit
        # beneficiary account number (same-bank transfer).
        for rec in self.filtered(lambda l: l.bank == "KASITHBK"):
            if any(
                len(sanitize_account_number(line.payment_partner_bank_id.acc_number))
                != 10
                for line in rec.export_line_ids
            ):
                raise UserError(_("Account Number must only be 10 digits."))
        return res
