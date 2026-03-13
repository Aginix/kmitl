from odoo import fields, models


class AdvancePaymentBank(models.Model):
    """Master data for banks used in advance payment agreements."""

    _name = "advance.payment.bank"
    _description = "Advance Payment Bank"
    _order = "name"

    name = fields.Char(string="Bank Name", required=True)
    active = fields.Boolean(default=True)
