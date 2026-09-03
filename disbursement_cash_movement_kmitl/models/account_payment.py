# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        """Append the cash-movement legs after the lines core (and
        ``finance_kmitl``, for withholding tax) already built.

        Scoped to disbursement vouchers with a route on file (Q9): a route with
        no hops means "pays directly", which adds nothing here either.
        """
        stale = self.env.context.get("kmitl_cash_route_resync") or ()
        if self.id in stale and write_off_line_vals:
            route = self.env["kmitl.cash.route"]._for_payment(self)
            movement_accounts = (
                route.hop_ids.account_id | route.paying_gl_account_id
            ).ids
            write_off_line_vals = [
                vals
                for vals in write_off_line_vals
                if vals.get("account_id") not in movement_accounts
            ]
        line_vals_list = super()._prepare_move_line_default_vals(write_off_line_vals)
        if not self.disbursement_request_id:
            return line_vals_list
        route = self.env["kmitl.cash.route"]._for_payment(self)
        if not route or not route.hop_ids:
            return line_vals_list
        liquidity = line_vals_list[0]
        return line_vals_list + route._leg_vals(liquidity, self)

    def _seek_for_lines(self):
        """Cash-movement legs are writeoff lines, never liquidity.

        ``_get_valid_liquidity_accounts`` counts every หัวจ่าย on the PV
        journal (``outbound_payment_method_line_ids.payment_account_id``), not
        only this payment's own — and a route's intermediate accounts, and
        sometimes the paying account itself, are themselves หัวจ่าย on other
        rows. Left alone, that would make more than one line look like "the"
        liquidity line and core would refuse to synchronise
        ("must include one and only one outstanding ... account"). Classifying
        by the flag first, ahead of the account-based test, is what keeps
        these legs out of liquidity regardless of whose account they share.
        """
        liquidity, counterpart, writeoff = super()._seek_for_lines()
        movement = liquidity.filtered("is_cash_movement_line")
        return liquidity - movement, counterpart, writeoff + movement

    def _synchronize_to_moves(self, changed_fields):
        """Keep cash-movement legs out of core's write-off merge.

        Core's rebuild folds every line ``_seek_for_lines`` calls writeoff into
        one dict, taking the name/account/partner/currency of the first and
        summing the rest into it — correct for a genuine write-off, wrong for
        our legs: they are Dr/Cr mirror pairs that always net to zero, so an
        unguarded merge would hand ``_prepare_move_line_default_vals`` one
        bogus zero-amount line on every voucher that carries a route but no
        withholding tax. Flagging the payment here lets that method drop the
        merged dict and rebuild the real legs fresh instead — the same
        context-passing trick ``finance_kmitl`` already uses to protect the
        withholding-tax write-off through this same rebuild. Nothing goes
        stale: core deletes every old writeoff line (ours included) as part of
        the same rewrite.
        """
        if self.env.context.get("skip_account_move_synchronization") or not any(
            field in changed_fields for field in self._get_trigger_fields_to_synchronize()
        ):
            return super()._synchronize_to_moves(changed_fields)
        flagged = self.filtered(
            lambda pay: pay._seek_for_lines()[2].filtered("is_cash_movement_line")
        )
        if not flagged:
            return super()._synchronize_to_moves(changed_fields)
        records = self.with_context(kmitl_cash_route_resync=flagged.ids)
        return super(AccountPayment, records)._synchronize_to_moves(changed_fields)
