from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WorkCenterMoveWizard(models.TransientModel):
    """Asks for what a move needs — the station to divert to, and the reason
    that forwarding without a required act, diverting and sending back all
    leave in the visit log — then calls the engine on the document."""

    _name = "work.center.move.wizard"
    _description = "Move a Document Between Stations"

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    mode = fields.Selection(
        selection=[
            ("forward", "Forward"),
            ("divert", "Divert"),
            ("send_back", "Send Back"),
        ],
        required=True,
    )
    # The station the screen showed. A move from a stale screen is refused.
    expected_station_id = fields.Integer()
    allowed_target_ids = fields.Many2many(
        comodel_name="work.center",
        compute="_compute_allowed_target_ids",
        string="Allowed Stations",
    )
    target_id = fields.Many2one(
        comodel_name="work.center",
        string="Divert To",
        domain="[('id', 'in', allowed_target_ids)]",
    )
    missing_act_ids = fields.Many2many(
        comodel_name="work.center.act",
        compute="_compute_missing_act_ids",
        string="Acts Still to Do",
    )
    needs_reason = fields.Boolean(compute="_compute_needs_reason")
    reason = fields.Text()

    def _document(self):
        self.ensure_one()
        document = self.env[self.res_model].browse(self.res_id).exists()
        if not document:
            raise UserError(_("This document no longer exists."))
        return document

    @api.depends("res_model", "res_id", "mode")
    def _compute_allowed_target_ids(self):
        for wizard in self:
            targets = self.env["work.center"]
            if wizard.mode == "divert" and wizard.res_model in self.env:
                document = wizard._document()
                if document._work_center_holding_station():
                    targets = document._work_center_divert_targets()
            wizard.allowed_target_ids = targets

    @api.depends("res_model", "res_id", "mode")
    def _compute_missing_act_ids(self):
        for wizard in self:
            missing = self.env["work.center.act"]
            if wizard.mode == "forward" and wizard.res_model in self.env:
                document = wizard._document()
                station = document._work_center_holding_station()
                if station and not station.is_unassigned:
                    missing = document._work_center_act_status(
                        document._work_center_open_visit(), station
                    )[0]
            wizard.missing_act_ids = missing

    @api.depends("mode", "missing_act_ids")
    def _compute_needs_reason(self):
        for wizard in self:
            wizard.needs_reason = bool(
                wizard.mode in ("divert", "send_back") or wizard.missing_act_ids
            )

    def action_confirm(self):
        self.ensure_one()
        document = self._document()
        reason = (self.reason or "").strip()
        expected = self.expected_station_id or None
        if self.mode == "forward":
            document._work_center_forward(reason, expected)
        elif self.mode == "divert":
            if not self.target_id:
                raise UserError(_("Choose the station to divert the document to."))
            document._work_center_divert(self.target_id, reason, expected)
        else:
            document._work_center_send_back(reason, expected)
        return {"type": "ir.actions.act_window_close"}
