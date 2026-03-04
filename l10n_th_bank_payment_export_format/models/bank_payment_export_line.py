# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
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
        return sanitize_account_number(acc_number)