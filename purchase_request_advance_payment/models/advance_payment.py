from odoo import _, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    def _is_reference_readonly(self):
        """Also lock reference when it already has a value (created from PR)."""
        result = super()._is_reference_readonly()
        if not result and self.reference:
            return True
        return result

    def _is_locked_by_reference(self):
        """Lock fields when the advance payment was created from a PR."""
        result = super()._is_locked_by_reference()
        if not result and self.reference:
            return True
        return result

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
