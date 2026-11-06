from odoo import api, fields, models


class AdvancePayment(models.Model):
    _name = "advance.payment"
    _inherit = ["advance.payment", "base.exception"]
    _order = "main_exception_id asc, name desc, id desc"

    # Read by excep_one_active_agreement (ADR-0001, a borrowing rule since
    # ADR-0030). Searched under sudo: an own-only borrower cannot see the
    # other agreement, and neither can the endorser the rule runs as.
    has_other_active_agreement = fields.Boolean(
        compute="_compute_has_other_active_agreement",
        help="Technical flag read by the one-active-agreement exception rule.",
    )

    @api.depends("employee_id", "state")
    def _compute_has_other_active_agreement(self):
        for rec in self:
            rec.has_other_active_agreement = bool(
                rec.employee_id
                and self.sudo().search_count(
                    [
                        ("employee_id", "=", rec.employee_id.id),
                        ("state", "in", self.ACTIVE_STATES),
                        ("id", "!=", rec._origin.id),
                    ],
                    limit=1,
                )
            )

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

        The permission check runs first, as it did before the split, so a
        request that may not be submitted at all says so instead of listing
        its exceptions."""
        self._check_submit_permission()
        for rec in self.filtered(lambda r: r.state == "draft"):
            if not rec.ignore_exception and rec.detect_exceptions():
                return rec._popup_exceptions()
        return super().action_submit()
