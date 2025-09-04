# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.depends("estimated_cost", "state")
    def _compute_is_egp(self):
        for record in self:
            if record.state == "approved":
                record.is_egp = record.estimated_cost > 100000
            else:
                record.is_egp = False
