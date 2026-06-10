from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_view_purchase_guarantee(self):
        action = super().action_view_purchase_guarantee()
        action["context"]["default_analytic_distribution"] = self.analytic_distribution
        return action
