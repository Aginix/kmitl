# -*- coding: utf-8 -*-
from odoo import models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def action_view_purchase_guarantee(self):
        action = super().action_view_purchase_guarantee()
        action["context"]["default_operating_unit_id"] = self.operating_unit_id.id
        return action
