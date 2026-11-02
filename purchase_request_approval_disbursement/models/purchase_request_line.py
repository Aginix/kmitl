# -*- coding: utf-8 -*-
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    def _prepare_disbursement_request_line_vals(self):
        return {
            "name": self.name,
            "amount": self.product_qty * self.price_unit,
            "analytic_distribution": self.analytic_distribution,
            "tax_ids": [Command.set(self.tax_id.ids)],
        }
