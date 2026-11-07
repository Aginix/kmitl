from odoo import _, api, models
from odoo.exceptions import ValidationError


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    @api.constrains("partner_id", "request_id")
    def _check_legacy_advance_borrower(self):
        """A เงินยืม (ระบบเก่า) request pays the borrower only."""
        for line in self:
            request = line.request_id
            borrower = request.legacy_advance_employee_id.work_contact_id
            if (
                request.payment_type == "advance_legacy"
                and borrower
                and line.partner_id != borrower
            ):
                raise ValidationError(
                    _(
                        "The payee of a เงินยืม (ระบบเก่า) request must be its "
                        "borrower, %(borrower)s.",
                        borrower=borrower.display_name,
                    )
                )
