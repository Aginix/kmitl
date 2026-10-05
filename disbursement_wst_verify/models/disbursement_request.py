# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, models
from odoo.addons.disbursement.models.disbursement_return_source import (
    _ACT_DR_CONTINUE,
    _ACT_SOURCE_DONE,
    _resolve_todos,
)
from odoo.exceptions import UserError


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

    def _station_check(self, code):
        super()._station_check(code)
        if code == "verify" and self.returned_to_source:
            raise UserError(
                _(
                    "This request was returned to its source document. "
                    "Please wait for the correction to be confirmed before "
                    "validating."
                )
            )

    def _station_complete(self, code):
        super()._station_complete(code)
        if code != "verify":
            return
        self._clear_returned_to_verification()
        # The officer acted on the correction: auto-resolve the "continue
        # verification" / "correction submitted" To-Dos on both sides.
        _resolve_todos(self, _ACT_DR_CONTINUE)
        source = self._get_return_source()
        if source:
            _resolve_todos(source.sudo(), _ACT_SOURCE_DONE)
