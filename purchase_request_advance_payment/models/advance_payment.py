from odoo import _, api, fields, models


class AdvancePayment(models.Model):
    _inherit = "advance.payment"

    purchase_request_count = fields.Integer(
        compute="_compute_purchase_request_count",
    )

    @api.depends("reference")
    def _compute_purchase_request_count(self):
        for rec in self:
            rec.purchase_request_count = (
                1
                if rec.reference and rec.reference._name == "purchase.request"
                else 0
            )

    def action_view_purchase_request(self):
        self.ensure_one()
        if not self.reference or self.reference._name != "purchase.request":
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "purchase.request",
            "res_id": self.reference.id,
            "view_mode": "form",
            "target": "current",
        }

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
