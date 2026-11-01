# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _get_report_base_filename(self):
        """Return the base filename for the report."""
        self.ensure_one()
        return f"Disbursement Request-{self.display_name}"
