# -*- coding: utf-8 -*-
from odoo import fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # For project expenses the product is not chosen by hand — the request
    # stamps the project budget account's product (see disbursement.request »
    # _budget_account_line_product). Relaxed to required=False so a draft can be
    # saved while the product resolves; the view keeps it required for non-project
    # lines, and a blocking base.exception refuses a project code with no bound
    # product on submit. Attribute-only override — no compute — so it merges
    # cleanly with other budget-account-expense bridges.
    product_id = fields.Many2one(required=False)
