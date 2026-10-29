from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    _rec_names_search = ["name", "contract_number", "approval_request_id.name"]

    # Typed mirror of `reference`, and the borrower's picker for it: compute for
    # display, inverse for input, following the repo's analytic_distribution →
    # *_analytic_id idiom. `reference` stays the source of truth (ADR-0007); a
    # `domain` on a fields.Reference would apply to every model in its selection
    # and so cannot carry a per-model filter (advance_payment ADR-0023).
    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        compute="_compute_approval_request_id",
        inverse="_inverse_approval_request_id",
        store=True,
        readonly=False,
        index=True,
        ondelete="restrict",
        compute_sudo=False,
        copy=False,
    )

    approval_request_count = fields.Integer(
        compute="_compute_approval_request_count",
    )

    exceeds_ar_headroom = fields.Boolean(
        compute="_compute_exceeds_ar_headroom",
        help="Technical flag read by the borrowing-headroom exception rule.",
    )

    reference = fields.Reference(
        selection_add=[("approval.request", "Approval Request")],
    )

    # Its own compute, not an extension of core's _compute_reference: Odoo
    # protects every field of a compute group while one of them is inverted,
    # so sharing it left reference_model stale after the picker wrote
    # `reference` — and excep_missing_reference fired on a picked request.
    @api.depends("reference")
    def _compute_approval_request_id(self):
        for rec in self:
            ref = rec.reference
            rec.approval_request_id = (
                ref if ref and ref._name == "approval.request" else False
            )

    def _inverse_approval_request_id(self):
        """Picking a request writes it into `reference`, the source of truth."""
        for rec in self:
            if rec.approval_request_id:
                rec.reference = rec.approval_request_id
            elif rec.reference_model == "approval.request":
                rec.reference = False

    @api.onchange("approval_request_id")
    def _onchange_approval_request_id(self):
        """This picker stands in for the `reference` widget on AR-backed loans,
        so it has to run the same prefill: `reference` itself is only written by
        the inverse at save time, long after `_onchange_reference` could fire."""
        if self.approval_request_id:
            self._apply_vals_from_reference()

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        """The picker is only written into `reference` at save, so super's
        clear cannot see it — drop it here when the new type does not take
        approval requests."""
        super()._onchange_loan_type_id()
        if self.loan_type_id.reference_model != "approval.request":
            self.approval_request_id = False

    def _check_reference_status(self):
        res = super()._check_reference_status()
        ar = self.approval_request_id
        if not ar:
            return res
        if ar.state != "approved":
            raise ValidationError(
                _(
                    "Approval request %(name)s must be approved before it can"
                    " back a loan (current status: %(state)s).",
                    name=ar.name,
                    state=dict(ar._fields["state"].selection).get(ar.state),
                )
            )
        return res

    def _prepare_vals_from_reference(self):
        """Pull what the request can tell us. The amount is deliberately NOT
        prefilled from the request total: each borrower declares their own
        (ADR-0003), bounded by the request's Borrowing Headroom."""
        vals = super()._prepare_vals_from_reference()
        ar = self.approval_request_id
        if ar:
            vals.update(
                {
                    "loan_reason": ar.description or "",
                }
            )
        return vals

    def _get_reference_picker_domain(self):
        """Approved requests, ANDed with the loan type's own filter
        (advance_payment ADR-0023). The participant roster is no longer a
        condition (advance_payment ADR-0025): who may borrow is left to the
        filter and to approval.request's own record rules."""
        domain = super()._get_reference_picker_domain()
        if self.loan_type_id.reference_model == "approval.request":
            domain = expression.AND([domain, [("state", "=", "approved")]])
        return domain

    @api.depends("approval_request_id")
    def _compute_approval_request_count(self):
        for rec in self:
            rec.approval_request_count = 1 if rec.approval_request_id else 0

    @api.depends(
        "loan_amount",
        "approval_request_id.borrowing_headroom",
        "approval_request_id.advance_payment_ids.loan_amount",
        "approval_request_id.advance_payment_ids.state",
    )
    def _compute_exceeds_ar_headroom(self):
        for rec in self:
            # sudo: a technical flag the exception rule reads — it must not
            # AccessError for an endorser with no approval.request access
            # (advance_payment_endorser_rule, advance_payment ADR-0020).
            ar = rec.approval_request_id.sudo()
            if not ar:
                rec.exceeds_ar_headroom = False
                continue
            # Headroom excluding this loan, so an already-counted draft does not
            # block itself.
            available = ar.borrowing_headroom
            if rec.state != "cancel":
                available += rec.loan_amount
            rec.exceeds_ar_headroom = bool(
                ar.borrowing_cap
                and rec.currency_id.compare_amounts(rec.loan_amount, available) > 0
            )

    def action_view_approval_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
