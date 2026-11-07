from odoo import fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    payment_type = fields.Selection(
        selection_add=[("budget_transfer", "Budget Transfer")],
        ondelete={"budget_transfer": "set null"},
    )
