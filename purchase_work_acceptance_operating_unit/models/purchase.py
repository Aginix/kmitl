# -*- coding: utf-8 -*-
from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_view_wa(self):
        result = super().action_view_wa()
        result["context"]["default_operating_unit_id"] = self.operating_unit_id.id
        return result
