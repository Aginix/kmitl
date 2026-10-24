# -*- coding: utf-8 -*-
from odoo import fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # For project expenses the account is not chosen by hand — the request
    # stamps the GL account sharing the budget code (see disbursement.request »
    # _budget_account_default_account). Relaxed to required=False so a draft can be
    # saved while the account resolves; the view keeps it required for non-project
    # lines, and a blocking base.exception refuses a project code with no
    # resolvable account on submit. Attribute-only override — no compute — so it
    # merges cleanly with other budget-account-expense bridges.
    account_id = fields.Many2one(required=False)
