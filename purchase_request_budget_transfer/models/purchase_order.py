from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    payment_type = fields.Selection(
        selection_add=[("budget_transfer", "Budget Transfer")],
        ondelete={"budget_transfer": "set null"},
    )
