# -*- coding: utf-8 -*-
from odoo import _, Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    def _prepare_disbursement_request_line_vals(self):
        account = (
            self.product_id.property_account_expense_id
            or self.product_id.categ_id.property_account_expense_categ_id
        )
        return {
            "product_id": self.product_id.id,
            "name": self.name,
            "quantity": self.product_qty,
            "price_unit": self.price_unit,
            "account_id": account.id if account else False,
            "analytic_distribution": self.analytic_distribution,
        }
