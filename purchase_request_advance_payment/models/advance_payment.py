from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    _rec_names_search = ["name", "contract_number", "purchase_request_id.name"]

    # Typed mirror of `reference` when it points at a purchase request: gives
    # searching, grouping and referential integrity that a bare Reference
    # (a Char at database level) cannot.
    purchase_request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        compute="_compute_reference",
        store=True,
        index=True,
        ondelete="restrict",
        compute_sudo=False,
    )

    purchase_request_count = fields.Integer(
        compute="_compute_purchase_request_count",
    )

    @api.depends("reference")
    def _compute_reference(self):
        super()._compute_reference()
        for rec in self:
            rec.purchase_request_id = (
                rec.reference if rec.reference_model == "purchase.request" else False
            )

    @api.depends("purchase_request_id")
    def _compute_purchase_request_count(self):
        for rec in self:
            rec.purchase_request_count = 1 if rec.purchase_request_id else 0

    _ALLOWED_PR_STATES_FOR_LOAN = ("approved", "to_submit", "to_approve", "in_egp")

    def _check_reference_status(self):
        res = super()._check_reference_status()
        pr = self.purchase_request_id
        if pr and pr.state not in self._ALLOWED_PR_STATES_FOR_LOAN:
            raise ValidationError(
                _(
                    "Purchase request %(name)s cannot back a loan in its"
                    " current status (%(state)s).",
                    name=pr.name,
                    state=dict(pr._fields["state"].selection).get(pr.state),
                )
            )
        return res

    def _prepare_vals_from_reference(self):
        """Pull the loan values off the source purchase request — the mirror of
        purchase.request._prepare_advance_payment_vals for the manual path."""
        vals = super()._prepare_vals_from_reference()
        pr = self.purchase_request_id
        if pr:
            vals.update(
                {
                    "requested_by": pr.requested_by.id,
                    "loan_amount": pr.get_estimated_cost_currency(),
                    "loan_reason": pr.description or "",
                    "analytic_distribution": pr.analytic_distribution,
                    "budget_commitment_id": pr.budget_commitment_id.id,
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
