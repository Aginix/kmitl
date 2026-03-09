from odoo import fields, models


class CreateGuaranteePaymentWizard(models.TransientModel):
    _name = "create.guarantee.payment.wizard"
    _description = "Create Payment from Guarantee"

    purchase_guarantee_id = fields.Many2one(
        comodel_name="purchase.guarantee",
        required=True,
        readonly=True,
    )
    kmitl_payment_type_id = fields.Many2one(
        comodel_name="kmitl.payment.type",
        string="Payment Type (KMITL)",
        required=True,
    )

    def action_create_payment(self):
        self.ensure_one()
        guarantee = self.purchase_guarantee_id
        payment_type = self.kmitl_payment_type_id
        vals = {
            "partner_id": guarantee.partner_id.id,
            "amount": guarantee.amount,
            "currency_id": guarantee.currency_id.id,
            "purchase_guarantee_id": guarantee.id,
            "kmitl_payment_type_id": payment_type.id,
            "payment_type": payment_type.direction,
        }
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
