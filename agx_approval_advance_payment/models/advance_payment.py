from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    _rec_names_search = ["name", "contract_number", "approval_request_id.name"]

    # Typed mirror of `reference`, and the borrower's picker for it: compute for
    # display, inverse for input, following the repo's analytic_distribution →
    # *_analytic_id idiom. `reference` stays the source of truth (ADR-0007); a
    # `domain` on a fields.Reference would apply to every model in its selection
    # and so cannot express "requests I am a participant of" (ADR-0003).
    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        string="Approval Request",
        compute="_compute_reference",
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

    # Sum of the request's เงินยืม allocation rows that name this loan as their
    # Funding Loan — used to prefill the expense report and to warn on drift.
    allocation_expense_amount = fields.Monetary(
        string="ค่าใช้จ่ายจริงตามใบขออนุมัติ",
        compute="_compute_allocation_expense_amount",
    )

    has_expense_divergence = fields.Boolean(
        compute="_compute_allocation_expense_amount",
    )

    exceeds_ar_headroom = fields.Boolean(
        compute="_compute_exceeds_ar_headroom",
        help="Technical flag read by the borrowing-headroom exception rule.",
    )

    reference = fields.Reference(
        selection_add=[("approval.request", "Approval Request")],
    )

    @api.depends("reference")
    def _compute_reference(self):
        super()._compute_reference()
        for rec in self:
            rec.approval_request_id = (
                rec.reference if rec.reference_model == "approval.request" else False
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
        # Only a participant may borrow against a request (ADR-0003). The UI
        # domain already filters this; enforce it for RPC / import too.
        if self.requested_by.partner_id not in ar.participant_ids.partner_id:
            raise ValidationError(
                _(
                    "%(user)s is not listed as a participant of %(name)s, so"
                    " cannot borrow against it.",
                    user=self.requested_by.name,
                    name=ar.name,
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
                    "analytic_distribution": ar.analytic_distribution,
                    # The request's own earmark — the loan rides it rather than
                    # reserving again (ADR-0003).
                    "budget_commitment_id": ar.budget_commitment_id.id,
                }
            )
        return vals

    @api.depends("approval_request_id", "reference", "loan_type_id.reference_model")
    def _compute_reference_state(self):
        super()._compute_reference_state()
        for rec in self:
            if rec.approval_request_id:
                rec.is_reference_visible = True

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        """Keep an approval-request reference when the picked loan type declares
        no reference_model — AR-backed loans use loan_type_other. A type that
        requires a *different* model still clears it (handled by super)."""
        if self.approval_request_id and not self.loan_type_id.reference_model:
            return
        super()._onchange_loan_type_id()

    @api.depends("approval_request_id")
    def _compute_approval_request_count(self):
        for rec in self:
            rec.approval_request_count = 1 if rec.approval_request_id else 0

    @api.depends(
        "actual_expense_amount",
        "approval_request_id.allocation_ids.amount",
        "approval_request_id.allocation_ids.advance_payment_id",
    )
    def _compute_allocation_expense_amount(self):
        for rec in self:
            rows = rec.approval_request_id.allocation_ids.filtered(
                lambda a, r=rec: a.advance_payment_id == r
            )
            total = sum(rows.mapped("amount"))
            rec.allocation_expense_amount = total
            rec.has_expense_divergence = bool(rows) and bool(
                rec.currency_id.compare_amounts(rec.actual_expense_amount, total)
            )

    @api.depends(
        "loan_amount",
        "approval_request_id.borrowing_headroom",
        "approval_request_id.advance_payment_ids.loan_amount",
        "approval_request_id.advance_payment_ids.state",
    )
    def _compute_exceeds_ar_headroom(self):
        for rec in self:
            ar = rec.approval_request_id
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

    def action_prefill_expense_from_allocation(self):
        """Fill the expense report from the request's เงินยืม rows naming this
        loan. Prefill, not derive: the borrower still confirms and submits it,
        because the debt is theirs (ADR-0005)."""
        self.ensure_one()
        rows = self.approval_request_id.allocation_ids.filtered(
            lambda a: a.advance_payment_id == self
        )
        if not rows:
            raise ValidationError(
                _("There are no เงินยืม rows on %(name)s naming this agreement yet.",
                  name=self.approval_request_id.display_name)
            )
        self.write(
            {
                "actual_expense_amount": sum(rows.mapped("amount")),
                "expense_description": "\n".join(
                    "- %s %s: %s"
                    % (
                        row.partner_id.display_name,
                        row.product_id.display_name or "",
                        row.amount,
                    )
                    for row in rows
                ),
            }
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
