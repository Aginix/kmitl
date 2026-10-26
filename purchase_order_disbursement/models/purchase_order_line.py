# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_disbursement_request_line_vals(self):
        return {
            "name": self.name,
            "amount": self.product_qty * self.price_unit,
            "tax_ids": [Command.set(self.taxes_id.ids)],
            "analytic_distribution": self.analytic_distribution,
        }
