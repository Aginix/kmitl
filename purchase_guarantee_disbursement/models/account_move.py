from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        # Receipt: payment linked to guarantee → lock → received
        payments = self.env["account.payment"].search([
            ("move_id", "in", posted.ids),
            ("purchase_guarantee_id", "!=", False),
        ])
        for payment in payments:
            guarantee = payment.purchase_guarantee_id
            if guarantee.state == "lock":
                guarantee.state = "received"
        # Refund: bill linked to guarantee → received → returned
        for move in posted:
            for guarantee in move.return_guarantee_ids:
                if guarantee.state == "received":
                    guarantee.state = "returned"
        return posted
