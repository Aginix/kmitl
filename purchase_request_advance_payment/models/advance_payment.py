from odoo import _, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    def _prepare_vals_from_reference(self):
        """Auto-fill fields from linked purchase request."""
        vals = super()._prepare_vals_from_reference()
        if self.reference and self.reference._name == "purchase.request":
            pr = self.reference
            vals.update(
                {
                    "requested_by": pr.requested_by.id,
                    "department_id": pr.department_id.id,
                    "loan_amount": pr.get_estimated_cost_currency(),
                    "loan_reason": pr.title or pr.description or "",
                    "analytic_distribution": pr.analytic_distribution,
                }
            )
        return vals

    def action_start(self, payment=None):
        """Override to cross-post disbursement message to linked purchase request."""
        res = super().action_start(payment=payment)
        for rec in self:
            if not rec.reference:
                continue
            ref_model, ref_id = rec.reference._name, rec.reference.id
            if ref_model != "purchase.request":
                continue
            pr = self.env["purchase.request"].browse(ref_id)
            if not pr.exists():
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
