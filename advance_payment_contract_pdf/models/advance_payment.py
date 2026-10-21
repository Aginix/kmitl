from datetime import datetime

from odoo import fields, models

from odoo.addons.thai_date_utils.models.thai_date_mixin import MONTHS_TH


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    def _contract_date_th(self, value):
        """Format a Date/Datetime as a Thai long date for the printed
        contract, e.g. ``23 กรกฎาคม 2569``. Returns "" when empty."""
        if not value:
            return ""
        if isinstance(value, datetime):
            value = fields.Datetime.context_timestamp(self, value)
        return f"{value.day} {MONTHS_TH[value.month]} {value.year + 543}"
