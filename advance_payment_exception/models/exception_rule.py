from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    advance_payment_ids = fields.Many2many(
        comodel_name="advance.payment",
        string="Advance Payments",
    )

    model = fields.Selection(
        selection_add=[
            ("advance.payment", "Advance Payment"),
        ],
        ondelete={"advance.payment": "cascade"},
    )
