# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _prepare_disbursement_request_vals(self):
        vals = super()._prepare_disbursement_request_vals()
        # The PO lines' dimensions (set by purchase_order_disbursement) win.
        vals.setdefault("analytic_distribution", self.analytic_distribution)
        vals.update({
            "budget_account_id": self.budget_account_id.id,
            "account_fiscal_year_id": self.account_fiscal_year_id.id,
            "budget_commitment_id": self.budget_commitment_id.id,
        })
        return vals
