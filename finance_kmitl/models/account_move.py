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

    # -------------------------------------------------------------------------
    # Withholding-tax certificates issued by the finance office (ADR-0008)
    # -------------------------------------------------------------------------
    @api.depends("payment_id.wht_cert_ids.state")
    def _compute_wht_cert_status(self):
        """Count the certificate the finance office issued on the voucher.

        A certificate raised from the voucher deliberately hangs off the payment
        and not off this entry, so that posting cannot delete it. The cost is that
        the entry cannot see it — and the banner offering to create one reads this
        field, so an accountant opening a voucher whose payee already has their
        50 ทวิ would be invited to issue a second one.

        The base ``@api.depends`` is not repeated: overriding a compute keeps the
        method name, and Odoo unions the dependencies declared for it across the
        inheritance chain.
        """
        super()._compute_wht_cert_status()
        for move in self:
            if not move.has_wht:
                continue
            certs = move.wht_cert_ids | move.payment_id.wht_cert_ids
            if not certs:
                continue
            states = set(certs.mapped("state"))
            if "draft" in states:
                move.wht_cert_status = "draft"
            elif "done" in states:
                move.wht_cert_status = "done"
            elif "cancel" in states:
                move.wht_cert_status = "cancel"

    def create_wht_cert(self):
        """Refuse a second certificate for a payee who already holds one.

        The accounting office reaches this through the banner on the entry, and
        the certificate the finance office issued is invisible from there (it
        belongs to the voucher). Two certificates for one withholding is two
        different papers the payee could file.
        """
        self.ensure_one()
        live = self.payment_id.wht_cert_ids.filtered(
            lambda cert: cert.state != "cancel"
        )
        if live:
            raise UserError(
                _(
                    "%(payment)s already has a withholding-tax certificate "
                    "(%(cert)s), issued by the finance office. Cancel it before "
                    "issuing another."
                )
                % {
                    "payment": self.payment_id.display_name,
                    "cert": live[:1].display_name,
                }
            )
        return super().create_wht_cert()

    def _prepare_withholding_move(self, wht_move):
        """Keep the type of income the finance office chose.

        Upstream reads it off the tax, which only ever gives the tax's default —
        so a voucher withheld under one rate but for a different kind of income
        would file under the wrong heading. The voucher records the answer
        (``account.payment.wht_cert_income_type``); this carries it into the
        withholding move, which is what the ภ.ง.ด. reports are built from.
        """
        vals = super()._prepare_withholding_move(wht_move)
        income_type = self.payment_id.wht_cert_income_type
        if income_type:
            vals["wht_cert_income_type"] = income_type
        return vals

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
