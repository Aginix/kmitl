from odoo import models


class BudgetMove(models.Model):
    _inherit = "budget.move"

    def _prepare_reversal_defaults(self):
        """A transfer's reversal is a plain budget move, not a transfer
        (budget ADR-0020): it carries no BTR of its own."""
        defaults = super()._prepare_reversal_defaults()
        defaults["is_transfer"] = False
        return defaults
