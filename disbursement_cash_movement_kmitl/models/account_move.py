# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _is_missing_cash_route(self):
        """Whether this voucher ought to travel a cash route but none is set up.

        The "setup gap" the non-blocking exception warns about at Submit, and
        deliberately *not* the same thing as having no legs: a route whose
        ``hop_ids`` is empty says "spent directly out of this account" and is
        silent, as is เงินสด, which has no bank account to be swept into.

        Lives here rather than in the rule's own ``code`` field because that
        field is evaluated by ``safe_eval`` against a bare context — no
        ``env`` — so logic written there is neither linted nor reachable by a
        test until it raises in front of an accountant.
        """
        self.ensure_one()
        payment = self.payment_id
        if not payment.disbursement_request_id:
            return False
        if not payment.payment_method_line_id.bank_account_id:
            return False
        return not self.env["kmitl.cash.route"]._for_payment(payment)

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
