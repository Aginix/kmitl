from odoo import fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # For procurement-plan expenses the account is derived from the budget
    # account, so a draft can carry a blank account while it resolves; the view
    # keeps it required for ordinary lines, and a blocking base.exception refuses
    # a procurement-plan code with no resolvable account on submit (a clear
    # message instead of a raw "account required" error). Attribute-only
    # override — no compute — so it merges cleanly with other
    # budget-account-expense bridges.
    account_id = fields.Many2one(required=False)
