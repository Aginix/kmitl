# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _all_payments_paid(self):
        """Every live voucher of the request has its money — and there is one."""
        self.ensure_one()
        active = self.payment_ids.filtered(lambda p: p.state != "cancel")
        return bool(active) and all(p.finance_state == "paid" for p in active)

    def _station_check(self, code):
        super()._station_check(code)
        if code == "pay" and not self._all_payments_paid():
            raise UserError(
                _("Every payment of the request must be paid before it can move on.")
            )

    def action_create_payment(self):
        """The finance office's way back in when the authorisation raised nothing.

        Normally the vouchers already exist by the time the request reaches them —
        authorising it is what raises them (ADR-0006). This is what is left for
        the cases where it could not: a banking coordinate that was wrong at the
        time, or a batch that was cancelled and is wanted again.
        """
        self.ensure_one()
        if self.station_code != "pay":
            raise UserError(
                _("The disbursement must be authorized before creating the payment.")
            )
        payments = self._create_payments()
        return {
            "type": "ir.actions.act_window",
            "name": _("Payments"),
            "res_model": "account.payment",
            "domain": [("id", "in", payments.ids)],
            "view_mode": "tree,form",
            "target": "current",
        }

    def action_confirm_paid(self):
        """The finance office's one confirmation that every payee has their money.

        It **writes** the outcome it asserts onto every payment rather than
        demanding that someone set it elsewhere first: the bank's own result file
        never enters Odoo, so no other record can know it, and asking the officer
        to tick each payee before ticking the request is a second pass over the
        same judgement. What is checked instead is a fact the system does hold —
        that the payments which travel in an e-payment file were actually put in
        one. Whatever the bank rejected was chased and settled outside the system
        before this is pressed.

        This is also the **Hand-over**: it is where the request stops being the
        finance office's and its vouchers enter the accounting office's approval
        queue. See ADR-0004.
        """
        for record in self:
            step = record.current_step_id
            if step.station_code != "pay":
                raise UserError(
                    _("Only a request waiting at the payment station can be confirmed as paid.")
                )
            step._check_act_allowed()
            active = record.payment_ids.filtered(lambda p: p.state != "cancel")
            if not active:
                raise UserError(
                    _("Create the payment(s) before confirming the payment.")
                )
            not_exported = active.filtered(
                lambda p: p.needs_bank_export and p.export_status != "exported"
            )
            if not_exported:
                raise UserError(
                    _(
                        "These payments have not left in an e-payment file yet: "
                        "%s. Put them in a file and mark it done before "
                        "confirming the payment."
                    )
                    % ", ".join(not_exported.mapped("name"))
                )
            # Every voucher raised by the authorisation was confirmed for the bank
            # there. One that reached the request another way — added by hand, or
            # unconfirmed to correct a coordinate and left that way — is confirmed
            # here instead: it is what gives it its number, and confirming it for a
            # bank says nothing this press does not already imply.
            active.filtered(
                lambda p: p.finance_state == "draft"
            ).action_confirm_for_bank()
            # Only the ones still waiting. Closing an e-payment file is itself
            # ยืนยันจ่ายสำเร็จ for the payees it carried, so by the time this press
            # happens most of a request is usually paid already — and ``_mark_paid``
            # refuses a voucher that is not ``confirmed``, so passing them all would
            # make this press fail on exactly the requests that had gone out
            # normally.
            active.filtered(
                lambda payment: payment.finance_state == "confirmed"
            )._mark_paid()
            # Usually a no-op by now: marking the last voucher paid crosses the
            # Hand-over on its own. It still matters for a request whose vouchers
            # were all paid before this press, where nothing was written and so
            # nothing fired.
            record._hand_over()
        return True

    def _hand_over(self):
        """The Hand-over: the request stops being the finance office's.

        Idempotent, and that is the point — it is reached two ways. Normally the
        last voucher turning paid brings the request across
        (``_try_hand_over_when_all_paid``); the finance office's own press calls it
        too, for the case where there was nothing left to mark. Only a request still
        at the pay station crosses, which is what keeps the accounting office from
        getting the same Todo twice.

        The payments being paid is the authority, not a person pressing a button,
        so the step is completed without the group check (the same shape as the
        billing station on the last bill posting).
        """
        for step in self.current_step_id.filtered(
            lambda s: s.station_code == "pay"
        ):
            step.sudo()._do_complete()
        return True

    def _try_hand_over_when_all_paid(self):
        """Cross the Hand-over once every payee of this request has their money.

        A request's payees can span several หัวจ่าย, so its vouchers go out in as
        many e-payment files, and no two of those files need be the same officer's.
        Nobody is therefore in a position to say "all of them are paid" on behalf of
        the others — so nobody is asked to. Each officer closes the file they
        handled, each closed file pays the vouchers it carried, and the request
        crosses when the last of them lands. The officer who happens to be last
        brings it across without having to know they were.

        A voucher still at ``draft`` — added by hand and never confirmed for the
        bank — holds the request here. That is intended: it has not been paid and
        the accounting office has nothing to book for it. What says so is the
        finance office's own Todo, which stays open, and จ่ายแล้ว n/m on the
        request.
        """
        for record in self:
            if record._all_payments_paid():
                record._hand_over()
        return True
