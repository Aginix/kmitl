from odoo import api, fields, models


class PurchaseGuarantee(models.Model):
    _inherit = "purchase.guarantee"

    payment_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="purchase_guarantee_id",
        string="Payments",
    )
    payment_count = fields.Integer(
        compute="_compute_payment_count",
    )

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for rec in self:
            rec.payment_count = len(rec.payment_ids)

    def action_view_payments(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_account_payments"
        )
        if self.payment_count == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = self.payment_ids.id
        else:
            action["domain"] = [("id", "in", self.payment_ids.ids)]
        return action

    def action_create_payment(self):
        self.ensure_one()
        payment_type = False
        if self.guarantee_method_id == self.env.ref("l10n_th_gov_purchase_guarantee.bid_guarantee"):
            payment_type = self.env.ref("account_payment_kmitl.payment_type_bid_guarantee_receive")
        elif self.guarantee_method_id == self.env.ref("l10n_th_gov_purchase_guarantee.advance_payment_guarantee"):
            payment_type = self.env.ref("account_payment_kmitl.payment_type_guarantee_receive")
        vals = {
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "purchase_guarantee_id": self.id,
        }
        if payment_type:
            vals.update({
                "kmitl_payment_type_id": payment_type.id,
                "payment_type": payment_type.direction,
            })
            if payment_type.journal_id:
                vals["journal_id"] = payment_type.journal_id.id
        payment = self.env["account.payment"].create(vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": payment.id,
            "view_mode": "form",
            "target": "current",
        }
