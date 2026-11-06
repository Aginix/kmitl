# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from markupsafe import Markup

from odoo import _, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _prepare_bill_vals(self, partner, partner_bank, invoice_lines):
        """Carry the memo number (เลขที่หนังสือ) into the bill's notes.

        Copied once when the bill is created: a later change to the
        request's memo number does not reach bills already created.
        """
        vals = super()._prepare_bill_vals(partner, partner_bank, invoice_lines)
        if self.memo_number:
            vals["narration"] = Markup("<p>%s</p>") % _(
                "Memo Number: %s", self.memo_number
            )
        return vals
