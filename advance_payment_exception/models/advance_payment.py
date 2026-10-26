from odoo import api, models


class AdvancePayment(models.Model):
    _name = "advance.payment"
    _inherit = ["advance.payment", "base.exception"]
    _order = "main_exception_id asc, name desc, id desc"

    @api.model
    def _reverse_field(self):
        return "advance_payment_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "advance_payment_exception.action_advance_payment_exception_confirm"
        )

    @api.constrains("ignore_exception", "loan_amount", "state")
    def advance_payment_check_exception(self):
        # Both pending states the record can sit in while its material fields
        # are still correctable: to_endorse is where action_submit lands it,
        # and to_verify is where the loan officer may still fix loan_amount /
        # bank_id / reference (ADR-0005) — those edits have to face the same
        # blocking rules the borrower did. excep_missing_manager scopes itself
        # out of to_verify, so a manager leaving mid-flight cannot false-block
        # the officer.
        records = self.filtered(lambda s: s.state in ("to_endorse", "to_verify"))
        if records:
            records._check_exception()

    def action_submit(self):
        """Stop a draft at the exceptions popup; super submits the rest.

        The permission and one-active checks run first, as they did before
        the split, so a request that may not be submitted at all says so
        instead of listing its exceptions."""
        self._check_submit_permission()
        for rec in self.filtered(lambda r: r.state == "draft"):
            rec._check_one_active_agreement()
            if not rec.ignore_exception and rec.detect_exceptions():
                return rec._popup_exceptions()
        return super().action_submit()
