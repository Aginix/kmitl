from odoo import fields, models


class AdvancePaymentType(models.Model):
    _name = "advance.payment.type"
    _description = "Advance Payment Type"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
