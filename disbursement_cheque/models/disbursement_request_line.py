# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # Requester-side only: finance still picks หัวจ่าย at audit.
    payment_method = fields.Selection(
        [("transfer", "Bank Transfer"), ("cheque", "Cheque")],
        default="transfer",
        required=True,
    )

    @api.depends("payment_method")
    def _compute_line_partner_bank_id(self):
        res = super()._compute_line_partner_bank_id()
        # A cheque payee needs no account; a frozen (submitted) line keeps
        # whatever it was checked against.
        for line in self:
            request = line.request_id
            if line.payment_method == "cheque" and (
                request.state in (False, "draft") or request.can_edit_lines
            ):
                line.partner_bank_id = False
        return res

    def _requires_partner_bank(self):
        return super()._requires_partner_bank() and self.payment_method == "transfer"
