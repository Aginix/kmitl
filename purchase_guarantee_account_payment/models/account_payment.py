from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    purchase_guarantee_id = fields.Many2one(
        comodel_name="purchase.guarantee",
        string="Purchase Guarantee",
        ondelete="set null",
        index=True,
    )
