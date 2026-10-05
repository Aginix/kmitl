# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    @api.depends("state", "station_code")
    def _compute_under_verification(self):
        super()._compute_under_verification()

    def _is_under_verification(self):
        self.ensure_one()
        return super()._is_under_verification() or (
            self.state == "in_progress" and self.station_code == "verify"
        )
