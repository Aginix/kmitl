# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _station_complete(self, code):
        super()._station_complete(code)
        if code == "approve_rector":
            # The single point where the budget is obligated and consumed.
            self._action_approve_budget()
