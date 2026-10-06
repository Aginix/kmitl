# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def _create_bill(self):
        self.ensure_one()
        if self.station_code != "bill":
            raise UserError(
                _("Bills can only be created while the request is at the billing station.")
            )
        return super()._create_bill()

    def _station_check(self, code):
        super()._station_check(code)
        if code == "bill":
            active = self.bill_ids.filtered(lambda b: b.state != "cancel")
            if not active or any(b.state != "posted" for b in active):
                raise UserError(
                    _("Every bill of the request must be posted before billing is done.")
                )

    def _on_bills_posted(self):
        """The last active bill is posted: the billing station is done.

        The posting itself (account.move approval) is the authority, so the step
        is completed without the button-press group check.
        """
        super()._on_bills_posted()
        step = self.current_step_id
        if step.station_code == "bill":
            step.sudo()._do_complete()
