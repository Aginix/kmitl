from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_open_in_new_tab(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web#model=purchase.order&id={self.id}&view_type=form",
            "target": "new",
        }
