# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        """Enforce the bank-export gate on the move-posting path.

        Outbound payments must be exported to the bank before posting. The
        guard also lives in account.payment.action_post, but the approval
        workflow posts the move (Approve = post) which can bypass that path,
        so it is enforced here as well.
        """
        for move in self:
            payment = move.payment_id
            if (
                payment
                and payment.payment_type == "outbound"
                and payment.export_status == "draft"
            ):
                raise UserError(
                    _("Payment must be exported to bank before posting.")
                )
        return super()._post(soft=soft)
