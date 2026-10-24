# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


class DisbursementRequestLine(models.Model):
    _inherit = "disbursement.request.line"

    # A new row's first onchange runs this too (account_id is in the line
    # list), so the row opens on the budget code's own account; the user may
    # still pick another one.
    @api.onchange("account_id")
    def _onchange_default_budget_account(self):
        if self.account_id:
            return
        self.account_id = self.request_id._budget_account_default_account()
        if not self.name:
            self.name = self.account_id.name
