from odoo import _, api, fields, models
from odoo.tools import plaintext2html


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    _rec_names_search = ["name", "contract_number", "purchase_request_id.name"]

    # The source model now lives here, not in core (advance_payment ADR-0023).
    reference = fields.Reference(
        selection_add=[("purchase.request", "Purchase Request")],
    )

    # Typed mirror of `reference` when it points at a purchase request: compute
    # for display, inverse for programmatic input, like
    # agx_approval_advance_payment's approval_request_id. Gives searching,
    # grouping and referential integrity that a bare Reference (a Char at
    # database level) cannot. The borrower names the request by its number
    # (`reference_number`, advance_payment ADR-0029).
    purchase_request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        compute="_compute_purchase_request_id",
        inverse="_inverse_purchase_request_id",
        store=True,
        readonly=False,
        index=True,
        ondelete="restrict",
        compute_sudo=False,
        copy=False,
    )

    purchase_request_count = fields.Integer(
        compute="_compute_purchase_request_count",
    )

    # Technical flags read by the borrowing rules (ADR-0030), under sudo: the
    # borrower, or the endorser a rule runs as, usually cannot read the
    # request.
    is_purchase_request_approved = fields.Boolean(
        compute="_compute_purchase_request_flags", compute_sudo=True
    )
    is_purchase_request_advance = fields.Boolean(
        compute="_compute_purchase_request_flags", compute_sudo=True
    )
    has_other_purchase_request_loan = fields.Boolean(
        compute="_compute_purchase_request_flags", compute_sudo=True
    )

    # Own compute, not core's _compute_reference: a shared compute group stays
    # protected while the picker's inverse writes `reference`, leaving
    # reference_model stale (see agx_approval_advance_payment).
    @api.depends("reference")
    def _compute_purchase_request_id(self):
        for rec in self:
            ref = rec.reference
            rec.purchase_request_id = (
                ref if ref and ref._name == "purchase.request" else False
            )

    def _inverse_purchase_request_id(self):
        """Picking a request writes it into `reference`, the source of truth."""
        for rec in self:
            if rec.purchase_request_id:
                rec.reference = rec.purchase_request_id
            elif rec.reference_model == "purchase.request":
                rec.reference = False

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        """Drop the mirror too when the new type does not take purchase
        requests."""
        super()._onchange_loan_type_id()
        if self.loan_type_id.reference_model != "purchase.request":
            self.purchase_request_id = False

    @api.depends(
        "purchase_request_id.state",
        "purchase_request_id.payment_type",
        "purchase_request_id.advance_payment_ids.state",
    )
    def _compute_purchase_request_flags(self):
        for rec in self:
            pr = rec.purchase_request_id
            rec.is_purchase_request_approved = pr.state == "approved"
            rec.is_purchase_request_advance = pr.payment_type == "advance"
            rec.has_other_purchase_request_loan = bool(
                pr
                and pr.advance_payment_ids.filtered(
                    lambda loan: loan.state != "cancel" and loan != rec._origin
                )
            )

    # Counted as the reader: a borrower who may not open the request sees no
    # button rather than one that opens an AccessError (ADR-0029).
    @api.depends("purchase_request_id")
    @api.depends_context("uid")
    def _compute_purchase_request_count(self):
        Request = self.env["purchase.request"]
        can_read = Request.check_access_rights("read", raise_exception=False)
        for rec in self:
            rec.purchase_request_count = (
                Request.search_count([("id", "=", rec.purchase_request_id.id)])
                if can_read and rec.purchase_request_id
                else 0
            )

    def _get_reference_summary(self):
        summary = super()._get_reference_summary()
        pr = self.purchase_request_id.sudo()
        if pr:
            summary.update(
                subject=pr.title
                or (pr.description or "").strip().split("\n")[0]
                or pr.name,
                unit=pr.requesting_department_id.display_name,
            )
        return summary

    def _prepare_vals_from_reference(self):
        """Pull the loan values off the named purchase request. The borrower
        is kept: anyone may borrow against a request, not only its requester
        (ADR-0029)."""
        vals = super()._prepare_vals_from_reference()
        # sudo: the borrower usually cannot read the request (ADR-0029).
        pr = self.purchase_request_id.sudo()
        if pr:
            vals.update(
                {
                    "loan_amount": pr.get_estimated_cost_currency(),
                    # "" not "<p></p>": an empty paragraph would satisfy the
                    # required reason.
                    "loan_reason": (
                        plaintext2html(pr.description) if pr.description else ""
                    ),
                }
            )
        return vals

    def action_view_purchase_request(self):
        self.ensure_one()
        if not self.purchase_request_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "res_id": self.purchase_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_start(self, payment=None):
        """Override to cross-post disbursement message to linked purchase request."""
        res = super().action_start(payment=payment)
        for rec in self:
            pr = rec.purchase_request_id
            if not pr:
                continue
            pr.message_post(
                body=_(
                    "สัญญายืมเงิน"
                    " <a href='/web#id=%(id)s&amp;model=advance.payment'>"
                    "<b>%(name)s</b></a>"
                    " ได้รับการเบิกจ่ายแล้ว จำนวน"
                    " <b>%(amount)s %(currency)s</b>",
                    id=rec.id,
                    name=rec.name,
                    amount=rec.loan_amount,
                    currency=rec.currency_id.name,
                ),
                subtype_xmlid="mail.mt_note",
            )
        return res
