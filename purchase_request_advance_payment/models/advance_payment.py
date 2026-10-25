from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import plaintext2html


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    _rec_names_search = ["name", "contract_number", "purchase_request_id.name"]

    # The source model now lives here, not in core (advance_payment ADR-0023).
    reference = fields.Reference(
        selection_add=[("purchase.request", "Purchase Request")],
    )

    # Typed mirror of `reference` when it points at a purchase request, and
    # the borrower's picker for it: compute for display, inverse for input,
    # like agx_approval_advance_payment's approval_request_id. Gives searching,
    # grouping and referential integrity that a bare Reference (a Char at
    # database level) cannot.
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

    @api.onchange("purchase_request_id")
    def _onchange_purchase_request_id(self):
        """This picker stands in for the `reference` widget, so it has to run
        the same prefill: `reference` itself is only written by the inverse at
        save time, long after `_onchange_reference` could fire."""
        if self.purchase_request_id:
            self._apply_vals_from_reference()

    @api.onchange("loan_type_id")
    def _onchange_loan_type_id(self):
        """The picker is only written into `reference` at save, so super's
        clear cannot see it — drop it here when the new type does not take
        purchase requests."""
        super()._onchange_loan_type_id()
        if self.loan_type_id.reference_model != "purchase.request":
            self.purchase_request_id = False

    def _get_reference_picker_domain(self):
        """Only approved advance-payment requests with no live loan of their
        own may back a loan — the same checks as _check_reference_status and
        _check_one_loan_per_purchase_request, offered up front (ADR-0023)."""
        domain = super()._get_reference_picker_domain()
        if self.loan_type_id.reference_model == "purchase.request":
            domain = expression.AND(
                [
                    domain,
                    [
                        ("state", "=", "approved"),
                        ("payment_type", "=", "advance"),
                        "|",
                        ("advance_payment_id", "=", False),
                        ("advance_payment_id", "=", self._origin.id),
                    ],
                ]
            )
        return domain

    @api.constrains("purchase_request_id", "state")
    def _check_one_loan_per_purchase_request(self):
        """A purchase request backs one live loan; a cancelled one frees it."""
        for rec in self.filtered(
            lambda r: r.purchase_request_id and r.state != "cancel"
        ):
            # sudo: an own-only borrower cannot see the other loan.
            other = self.sudo().search(
                [
                    ("purchase_request_id", "=", rec.purchase_request_id.id),
                    ("state", "!=", "cancel"),
                    ("id", "!=", rec.id),
                ],
                limit=1,
            )
            if other:
                raise ValidationError(
                    _(
                        "ใบขอให้จัดหา %(pr)s มีสัญญายืมเงิน %(loan)s อยู่แล้ว",
                        pr=rec.purchase_request_id.name,
                        loan=other.name,
                    )
                )

    @api.depends("purchase_request_id")
    def _compute_purchase_request_count(self):
        for rec in self:
            rec.purchase_request_count = 1 if rec.purchase_request_id else 0

    def _check_reference_status(self):
        res = super()._check_reference_status()
        pr = self.purchase_request_id
        if pr and pr.payment_type != "advance":
            raise ValidationError(
                _(
                    "ใบขอให้จัดหา %(name)s ไม่ได้เลือกวิธีจ่ายเป็นเงินยืม",
                    name=pr.name,
                )
            )
        if pr and pr.state != "approved":
            raise ValidationError(
                _(
                    "Purchase request %(name)s must be approved before it can"
                    " back a loan (current status: %(state)s).",
                    name=pr.name,
                    state=dict(pr._fields["state"].selection).get(pr.state),
                )
            )
        return res

    def _prepare_vals_from_reference(self):
        """Pull the loan values off the picked purchase request. The borrower
        is kept: anyone may borrow against a request, not only its requester
        (ADR-0026)."""
        vals = super()._prepare_vals_from_reference()
        pr = self.purchase_request_id
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
