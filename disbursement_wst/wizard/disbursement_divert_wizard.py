# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementDivertWizard(models.TransientModel):
    """Name the station that must look at a request, and say why."""

    _name = "disbursement.divert.wizard"
    _description = "Divert a Disbursement Request"

    request_id = fields.Many2one(
        "disbursement.request", required=True, readonly=True, ondelete="cascade"
    )
    current_station_id = fields.Many2one(
        "disbursement.station", related="request_id.current_step_id.station_id"
    )
    station_id = fields.Many2one(
        "disbursement.station",
        string="Send To",
        required=True,
        domain="[('id', '!=', current_station_id)]",
    )
    come_back = fields.Boolean(
        string="Come Back to Me",
        default=True,
        help="Queue this station again once the other one is done. Without it "
        "the request goes on along its route instead.",
    )
    note = fields.Text(string="Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        self.request_id.current_step_id.divert(
            self.station_id, self.come_back, self.note
        )
        return {"type": "ir.actions.act_window_close"}
