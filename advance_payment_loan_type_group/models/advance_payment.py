from odoo import _, api, models
from odoo.exceptions import ValidationError


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    @api.constrains("loan_type_id")
    def _check_loan_type_selectable(self):
        """The form only offers selectable types; this holds RPC and import to
        the same rule. Fires only when the type is set or changed, so a
        borrower may still edit a loan an officer drafted in a restricted
        type (ADR-0031)."""
        if self.env.su:
            return
        for rec in self:
            if rec.loan_type_id and not rec.loan_type_id.is_selectable:
                raise ValidationError(
                    _(
                        "คุณไม่มีสิทธิ์เลือกประเภทเงินยืม %(type)s",
                        type=rec.loan_type_id.name,
                    )
                )
