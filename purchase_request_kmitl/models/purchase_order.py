from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        ondelete="restrict",
        tracking=True,
    )
