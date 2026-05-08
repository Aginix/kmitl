from odoo import fields, models


class AdvancePaymentUsageLine(models.Model):
    _inherit = "advance.payment.usage.line"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="agreement_id.operating_unit_id",
        string="Operating Unit",
    )
