# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _wht_counterpart_leg_vals(self, vals):
        """The payable-side mirror of one withholding-tax write-off line.

        Every credit on a voucher gets its own debit against the payable,
        instead of leaving the payable's single line to be read against the tax
        line to be understood (``docs/adr/0001``). The mirror is that tax
        line's amount, sign-flipped, on the counterpart account this payment
        actually uses — the override account of its operation type, or the
        plain receivable/payable core would have used anyway.

        ``date_maturity`` is set explicitly: core sets it on the liquidity and
        counterpart lines it builds itself but never on a write-off line, and a
        stored, never-computed Date left NULL sorts the mirror into "not yet
        due" on both the Aged Payable Balance and the Open Items report that
        ``accounting_kmitl_reports`` ships, while the line it mirrors ages
        normally.
        """
        self.ensure_one()
        return {
            "name": vals["name"],
            "account_id": self.destination_account_id.id,
            "partner_id": vals["partner_id"],
            "currency_id": vals["currency_id"],
            "amount_currency": -vals["amount_currency"],
            "balance": -vals["balance"],
            "date_maturity": self.date,
            "is_wht_counterpart_line": True,
        }

    def _adjust_write_off_line_vals(self, write_off_line_vals):
        """Give every withholding-tax write-off line its own payable mirror.

        Runs on ``finance_kmitl``'s seam, after any preserved values are back in
        place and before core computes the counterpart from their sum — which
        is what makes the arithmetic free: the mirrors cancel the tax lines
        exactly, so core's own ``counterpart = -liquidity - sum(write_offs)``
        comes out at the amount that actually left the bank, and the tax's own
        debit is a line of its own rather than part of a lump sum.

        The mirrors already in the list are always dropped and rebuilt, never
        kept — a mirror whose tax line has lost its ``wht_tax_id`` (a maker
        cleared it) has to go even though nothing replaces it, or it would ride
        along as an ordinary write-off paired with the now-untagged line it used
        to mirror and leave the voucher with the wrong counterpart amount
        instead of degrading to the plain entry core would have built.

        ``None`` and ``False`` pass straight through: core defaults this
        argument to ``None`` and only turns it into a list inside its own
        method, and most payments — every one without a write-off — arrive here
        that way. The list is rebuilt rather than mutated because the one handed
        in belongs to the caller, sometimes the ``kmitl_preserved_write_off``
        context's.
        """
        write_off_line_vals = super()._adjust_write_off_line_vals(write_off_line_vals)
        if not write_off_line_vals:
            return write_off_line_vals
        incoming = [
            vals
            for vals in write_off_line_vals
            if not vals.get("is_wht_counterpart_line")
        ]
        mirrors = [
            self._wht_counterpart_leg_vals(vals)
            for vals in incoming
            if vals.get("wht_tax_id")
        ]
        return incoming + mirrors

    def _seek_for_lines(self):
        """Keep the WHT counterpart leg out of core's one-counterpart rule.

        A leg sits on the same account as the real counterpart line, so base's
        account-type test would count it too — and core requires exactly one
        ("must include one and only one receivable/payable account"). Moving it
        into writeoff_lines instead is what ``disbursement_cash_movement_kmitl``
        already does for its own extra Dr/Cr leg, for the same reason.
        """
        liquidity_lines, counterpart_lines, writeoff_lines = super()._seek_for_lines()
        mirrors = counterpart_lines.filtered("is_wht_counterpart_line")
        if mirrors:
            counterpart_lines -= mirrors
            writeoff_lines += mirrors
        return liquidity_lines, counterpart_lines, writeoff_lines

    def _preserved_write_off_lines(self):
        """Preserve the legs too, or a rebuild loses the money, not the name.

        Once ``_seek_for_lines`` has made a leg a write-off line, core's rebuild
        folds every write-off into one dict and sums their amounts into it — and
        a tax line of -130.84 with its mirror of +130.84 sums to 0.00, so core
        would replace both with a single empty line and the withheld tax would
        never be booked at all. Naming the legs here keeps them in
        ``finance_kmitl``'s stash, where ``_adjust_write_off_line_vals`` drops
        and rebuilds them; what core merges is then never used.
        """
        return super()._preserved_write_off_lines() | self._seek_for_lines()[
            2
        ].filtered("is_wht_counterpart_line")

    def _write_off_line_vals(self, line):
        """Carry the flag through the stash.

        Without it a preserved mirror would come back looking like an ordinary
        write-off line, and ``_adjust_write_off_line_vals`` could neither drop
        it nor tell it apart from the tax line it mirrors.
        """
        vals = super()._write_off_line_vals(line)
        vals["is_wht_counterpart_line"] = line.is_wht_counterpart_line
        return vals
