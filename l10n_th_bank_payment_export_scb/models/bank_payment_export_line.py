# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import api, fields, models

from odoo.addons.base.models.res_bank import sanitize_account_number


class BankPaymentExportLine(models.Model):
    _inherit = "bank.payment.export.line"

    scb_beneficiary_noti = fields.Selection(
        selection=[
            ("N", "N - None"),
            ("F", "F - Fax"),
            ("S", "S - SMS"),
            ("E", "E - Email"),
        ],
        compute="_compute_default_scb_config",
        store=True,
        readonly=False,
    )
    scb_beneficiary_phone = fields.Char(size=10)
    scb_beneficiary_email = fields.Char(size=64)
    scb_beneficiary_charge = fields.Boolean(
        compute="_compute_beneficiary_charge_line",
        store=True,
        readonly=False,
    )

    @api.depends("payment_partner_id")
    def _compute_default_scb_config(self):
        for rec in self:
            rec.scb_beneficiary_noti = rec.payment_partner_id.scb_beneficiary_noti
            rec.onchange_beneficiary_noti()

    @api.depends("payment_export_id.scb_beneficiary_charge")
    def _compute_beneficiary_charge_line(self):
        for rec in self:
            rec.scb_beneficiary_charge = rec.payment_export_id.scb_beneficiary_charge

    @api.onchange("scb_beneficiary_noti")
    def onchange_beneficiary_noti(self):
        if self.scb_beneficiary_noti == "E":
            self.scb_beneficiary_phone = self.scb_beneficiary_phone or False
            self.scb_beneficiary_email = self.payment_partner_id.scb_email_partner
        elif self.scb_beneficiary_noti == "F":
            self.scb_beneficiary_phone = self.payment_partner_id.scb_phone_partner
            self.scb_beneficiary_email = self.scb_beneficiary_email or False
        elif self.scb_beneficiary_noti == "S":
            self.scb_beneficiary_phone = self.payment_partner_id.scb_sms_partner
            self.scb_beneficiary_email = self.scb_beneficiary_email or False

    def _get_sender_information(self):
        (
            sender_bank_code,
            sender_branch_code,
            sender_acc_number,
        ) = super()._get_sender_information()
        if self.payment_export_id.bank == "SICOTHBK":
            sender_bank_code = (
                sender_bank_code and sender_bank_code[:3].zfill(3) or "---"
            )
            sender_branch_code = (
                sender_branch_code and sender_branch_code[:4].zfill(4) or "----"
            )
            sender_acc_number = (
                sender_acc_number and sender_acc_number[:11].zfill(11) or "-----------"
            )
        return sender_bank_code, sender_branch_code, sender_acc_number

    def _get_receiver_branch_code_scb(self):
        """Return the receiving branch code for a payee who banks at SCB.

        An SCB account number carries its branch in the first three digits --
        ``0882428018`` is branch 088 -- and that is what the bank's own file
        puts in this field: the real KMITL sample credits three accounts all
        starting ``088`` and writes ``0088`` for each. The debit side of the
        same layout already reads it that way (``scb_debit_format_07``).

        Reading it off ``res.bank.bank_branch_code`` instead, as this field used
        to, gives one branch for the whole of SCB, so the first payee banking at
        any other branch goes out misrouted -- and silently, because a
        well-formed four-digit code for the wrong branch looks exactly like a
        right one.
        """
        self.ensure_one()
        acc_number = (
            sanitize_account_number(self.payment_partner_bank_id.acc_number) or ""
        )
        return acc_number[:3].rjust(4, "0")

    def _get_acc_number_digit(self, partner_bank_id):
        """SCB credit-account formatting per product code.

        - DCP (Direct Credit): exactly 10 digits, zero-padded.
        - BNT / PAY / MCL / ...: the raw sanitized SCB account number
          (left-justified in the field). It must NOT be zero-filled to 11
          digits like the generic interbank formatter, which would prepend a
          spurious leading zero to a 10-digit SCB account (real sample shows
          a 10-digit credit account such as ``0882428018``).
        """
        if self.payment_export_id.bank == "SICOTHBK":
            sanitize_acc_number = (
                sanitize_account_number(partner_bank_id.acc_number) or ""
            )
            if self.payment_export_id.scb_product_code == "DCP":
                return sanitize_acc_number.zfill(10)
            return sanitize_acc_number
        return super()._get_acc_number_digit(partner_bank_id)
