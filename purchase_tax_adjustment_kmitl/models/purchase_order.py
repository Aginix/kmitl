from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "tax.adjustment.mixin"]

    tax_totals = fields.Binary(inverse="_inverse_tax_totals")

    @api.depends("order_line.price_subtotal", "order_line.price_tax")
    def _compute_tax_adjustment(self):
        return super()._compute_tax_adjustment()

    @api.depends("tax_adjustment")
    def _amount_all(self):
        res = super()._amount_all()
        self._apply_tax_adjustment_amounts()
        return res

    @api.depends("tax_adjustment")
    def _compute_tax_totals(self):
        res = super()._compute_tax_totals()
        self._apply_tax_adjustment_totals()
        return res
