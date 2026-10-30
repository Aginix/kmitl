from odoo import _, api, models
from odoo.exceptions import ValidationError


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    @api.constrains("partner_id", "request_id")
    def _check_advance_payment_borrower(self):
        """A ใบเบิกชดใช้เงินยืม pays the borrower only."""
        for line in self:
            loan = line.request_id.advance_payment_id.sudo()
            if loan and line.partner_id != loan.partner_id:
                raise ValidationError(
                    _(
                        "The payee of a request clearing loan %(loan)s must be "
                        "its borrower, %(borrower)s.",
                        loan=loan.contract_number or loan.name,
                        borrower=loan.partner_id.display_name,
                    )
                )
