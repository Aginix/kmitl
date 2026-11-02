# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # Requester-side only: finance still picks หัวจ่าย at audit. Blank on a
    # request that pays no money out (an advance).
    payment_method = fields.Selection(
        [("transfer", "Bank Transfer"), ("cheque", "Cheque")],
        compute="_compute_payment_method",
        store=True,
        readonly=False,
    )

    @api.depends("request_id.pays_out")
    def _compute_payment_method(self):
        for line in self:
            if not line.request_id.pays_out:
                line.payment_method = False
            elif not line.payment_method:
                line.payment_method = "transfer"

    @api.constrains("payment_method", "request_id")
    def _check_payment_method(self):
        for line in self:
            if line.request_id.pays_out and not line.payment_method:
                raise ValidationError(_("Payment method is required on each line."))

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
