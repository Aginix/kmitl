# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError

# What a journal item says about the money, as opposed to about the booking. The
# accounting maker edits the lines of a handed-over payment voucher — that is what
# their step is for — but the amount the bank paid, the account it left from and the
# payee are not theirs to move. Everything not listed here stays editable, which
# deliberately includes ``analytic_distribution`` (the correction they are usually
# there to make) and the technical fields reconciliation writes at posting time.
MONEY_LINE_FIELDS = (
    "debit",
    "credit",
    "balance",
    "amount_currency",
    "account_id",
    "partner_id",
    "currency_id",
    "date_maturity",
)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _payment_money_side_check(self, what):
        """Raise if a line here belongs to a voucher the bank already acted on.

        Skipped for Odoo's own payment synchronisation, which rebuilds these lines
        from the payment and is not a person editing the entry.
        """
        if self.env.context.get("skip_account_move_synchronization"):
            return True
        for line in self.filtered(lambda row: row.move_id.payment_id):
            line.move_id.payment_id._check_money_side_open(what)
        return True

    def write(self, vals):
        money = [name for name in vals if name in MONEY_LINE_FIELDS]
        if money:
            self._payment_money_side_check(
                ", ".join(
                    description["string"]
                    for description in self.fields_get(money, ["string"]).values()
                )
            )
        return super().write(vals)

    def unlink(self):
        self._payment_money_side_check(_("Journal items"))
        return super().unlink()
