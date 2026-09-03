# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        """Give a voucher whose dimensions arrived late one last chance to
        grow its cash-movement legs before it freezes.

        ``analytic_distribution`` is not one of ``account.payment``'s trigger
        fields for ``_synchronize_to_moves`` — it lives on the move via
        ``_inherits``, and core's own list names payment fields such as
        ``journal_id`` — so a voucher created before its source of funds was
        known, and therefore before its route could be looked up, never
        otherwise gets a second chance once the dimensions are filled in.
        Re-checked only for vouchers that resolve to a route with hops but
        currently carry no leg, so a correctly-built voucher is left
        untouched on every other post.
        """
        Route = self.env["kmitl.cash.route"]
        for move in self:
            payment = move.payment_id
            if not payment.disbursement_request_id:
                continue
            route = Route._for_payment(payment)
            if route.hop_ids and not move.line_ids.filtered("is_cash_movement_line"):
                payment._synchronize_to_moves(
                    payment._get_trigger_fields_to_synchronize()
                )
        return super()._post(soft=soft)
