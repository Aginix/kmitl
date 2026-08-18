# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # For project expenses the product is not chosen by hand — it is the product
    # bound to the project budget account (budget_product). Editable computed so
    # ordinary (non-project) disbursements keep picking their product manually.
    # Relaxed to required=False so a draft can be saved while the product resolves;
    # the view keeps it required for non-project lines, and a blocking
    # base.exception refuses a project code with no bound product on submit.
    product_id = fields.Many2one(
        compute="_compute_product_id_project",
        store=True,
        readonly=False,
        required=False,
    )

    @api.depends(
        "request_id.budget_account_id",
        "request_id.budget_account_id.is_project",
        "request_id.budget_account_id.product_id",
    )
    def _compute_product_id_project(self):
        for line in self:
            account = line.request_id.budget_account_id
            if account and account.is_project:
                line.product_id = account.product_id
            else:
                # Keep the manually picked product for non-project lines.
                line.product_id = line.product_id

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """For project expenses the product is only a budget-code mapping (its
        list price is a placeholder, its name is the budget item) — so keep the
        user's own description and amount, letting the base derive just the
        expense account. Ordinary lines keep the full base behaviour."""
        if self.request_id.budget_account_id.is_project:
            name, price = self.name, self.price_unit
            res = super()._onchange_product_id()
            self.name = name or self.name
            self.price_unit = price
            return res
        return super()._onchange_product_id()
