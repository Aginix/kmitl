from odoo import models


class BudgetMoveLine(models.Model):
    _inherit = "budget.move.line"

    def _reversal_key(self):
        """The coordinate a reversal nets against: budget code, bucket and
        every dimension the availability engine matches on."""
        self.ensure_one()
        return (
            self.account_id.id,
            self.move_type,
            tuple(sorted(self._ledger_coordinate())),
        )
