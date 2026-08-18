from odoo import fields, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # For procurement-plan expenses the product is derived from the budget
    # account, so a draft can carry a blank product while it resolves; the view
    # keeps it required for ordinary lines, and a blocking base.exception refuses
    # a procurement-plan code with no bound product on submit (a clear message
    # instead of a raw "product required" error). Attribute-only override — no
    # compute — so it merges cleanly with other budget-account-expense bridges.
    product_id = fields.Many2one(required=False)
