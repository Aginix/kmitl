from odoo import _, models
from odoo.exceptions import UserError


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    def action_open_partner_bank_wizard(self):
        """Open the สร้างบัญชีธนาคาร wizard, prefilled from the account the
        borrower declared, for the officer to check against the Book Bank
        (advance_payment ADR-0022)."""
        self.ensure_one()
        if self.state != "to_verify" or not self.use_unlisted_bank:
            raise UserError(
                _("Only an unlisted bank account under verification can be created.")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("สร้างบัญชีธนาคาร"),
            "res_model": "advance.payment.partner.bank.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_advance_payment_id": self.id,
                "default_partner_id": self.partner_id.id,
                "default_bank_id": self.unlisted_bank_id.id,
                "default_acc_number": self.unlisted_acc_number,
                "default_acc_holder_name": self.employee_id.name,
            },
        }
