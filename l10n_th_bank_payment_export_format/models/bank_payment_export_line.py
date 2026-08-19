import logging

from odoo import models, fields, api

from odoo.addons.base.models.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)


class BankPaymentExportLine(models.Model):
    _inherit = "bank.payment.export.line"

    # The sending side of the file — "Sending A/C" and its bank in the bank
    # layouts. Exposed as fields so a layout does not have to know where the
    # money leaves from: by default that is the bank account behind the
    # payment's journal, and a localisation that pays out of somewhere else
    # extends the compute.
    sending_bank_id = fields.Many2one(
        comodel_name="res.bank",
        compute="_compute_sending_account",
        string="Sending Bank",
    )
    sending_acc_number = fields.Char(
        compute="_compute_sending_account",
        string="Sending A/C Number",
    )

    @api.depends("payment_id.journal_id.bank_account_id")
    def _compute_sending_account(self):
        for line in self:
            journal_bank = line.payment_id.journal_id.bank_account_id
            line.sending_bank_id = journal_bank.bank_id
            line.sending_acc_number = journal_bank.acc_number

    def sanitize_account_number(self, acc_number):
        """
        Wrapper method to call sanitize_account_number function
        This allows the function to be called from safe_eval context
        """
        return sanitize_account_number(acc_number) or ""

    def _get_receiver_branch_code_gsb(self):
        """Return the receiving branch code for a Government Savings Bank
        (GSB, ``GSBATHBK``) recipient.

        Referenced by the KTB and SCB layouts for GSB recipients, which
        historically require special branch handling. Until the official bank
        specs are confirmed, fall back to the recipient bank's branch code so
        the export no longer raises ``AttributeError``.

        TODO: confirm the exact GSB branch-code/name derivation against the
        official KTB iPay and SCB BCM file-format specifications.
        """
        self.ensure_one()
        return self.payment_partner_bank_id.bank_id.bank_branch_code or ""
