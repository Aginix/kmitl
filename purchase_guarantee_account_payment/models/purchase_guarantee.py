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
        return {
            "type": "ir.actions.act_window",
            "res_model": "create.guarantee.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_purchase_guarantee_id": self.id,
            },
        }
