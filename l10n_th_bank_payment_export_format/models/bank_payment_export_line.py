# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.base.models.res_bank import sanitize_account_number
_logger = logging.getLogger(__name__)


class BankPaymentExportLine(models.Model):
    _inherit = 'bank.payment.export.line'

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