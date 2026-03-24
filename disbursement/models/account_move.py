# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        res = super().write(vals)
        if "payment_state" in vals:
            paid_moves = self.filtered(lambda m: m.payment_state == "paid")
            if paid_moves:
                disbursements = self.env["disbursement.request"].search([
                    ("bill_id", "in", paid_moves.ids),
                    ("state", "=", "in_progress"),
                ])
                disbursements.action_done()
        return res
