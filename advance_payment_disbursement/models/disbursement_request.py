from odoo import fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    advance_payment_id = fields.Many2one(
        "advance.payment",
        string="Advance Payment",
    )
