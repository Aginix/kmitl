from odoo import models


class BudgetTransfer(models.Model):
    # On the transfer, not on the budget.move it delegates to.
    _inherit = ["budget.transfer", "related.document.mixin"]
    _name = "budget.transfer"
