# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, models
from odoo.exceptions import UserError

from .account_payment import MONEY_FIELDS


class AccountMove(models.Model):
    _inherit = "account.move"

    def _is_handed_over_payment(self):
        """This entry is a payment voucher the finance office has finished with.

        From the Hand-over onwards the voucher is the accounting office's to book:
        they correct the booking side, submit it and approve it. See
        ``disbursement_finance_kmitl`` ADR-0005.
        """
        self.ensure_one()
        return self.payment_id.finance_state == "paid"

    def _check_submit_allowed(self):
        """A handed-over payment voucher may be submitted by any accounting maker.

        The creator rule guards an entry an accounting person typed — you do not
        submit a colleague's work. A voucher the finance office prepared and handed
        over has no accounting author at all, so there is no colleague's work to
        take over: its maker is whichever accounting person picks it up to book.
        """
        others = self.filtered(lambda move: not move._is_handed_over_payment())
        if others:
            super(AccountMove, others)._check_submit_allowed()
        return True

    @api.depends("create_uid", "payment_id.finance_state")
    @api.depends_context("uid")
    def _compute_can_submit(self):
        # Both dependencies are declared here on purpose: overriding a compute
        # replaces the base decorator rather than adding to it, so 'create_uid'
        # has to be carried over or the base rule would stop recomputing.
        super()._compute_can_submit()
        for move in self:
            if move._is_handed_over_payment():
                move.can_submit = True

    def write(self, vals):
        """Guard the money side of a payment voucher.

        The accounting maker works on this form, so this is where a change to the
        date, the journal, the payee or their bank account would be made — all of
        them facts the bank already acted on. Skipped for Odoo's own
        payment/entry synchronisation, which is how core rebuilds the entry from
        the payment and is not somebody editing the record.
        """
        money = [name for name in vals if name in MONEY_FIELDS]
        if money and not self.env.context.get("skip_account_move_synchronization"):
            label = ", ".join(
                description["string"]
                for description in self.fields_get(money, ["string"]).values()
            )
            for move in self.filtered("payment_id"):
                move.payment_id._check_money_side_open(label)
        return super().write(vals)

    def _post(self, soft=True):
        """Refuse to post a payment the finance office has not finished with.

        Two gates, both on the move-posting path because the approval workflow
        posts the move (Approve = post) and so bypasses
        ``account.payment.action_post``:

        * the voucher must have left in an e-payment file, if it travels in one;
        * the finance office must have said the money reached the payee.

        Which payments each applies to is the payment's own answer, so the two
        paths cannot drift apart.
        """
        for move in self:
            payment = move.payment_id
            if not payment:
                continue
            if payment.needs_bank_export and payment.export_status == "draft":
                raise UserError(_("Payment must be exported to bank before posting."))
            if payment.finance_state != "paid":
                raise UserError(
                    _(
                        "%s cannot be posted: the finance office has not confirmed "
                        "that the money reached the payee."
                    )
                    % payment.display_name
                )
        return super()._post(soft=soft)
