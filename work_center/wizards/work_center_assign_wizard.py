from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WorkCenterAssignWizard(models.TransientModel):
    """Asks a station administrator which responsible person of the station is
    to handle a document, then calls the engine on it."""

    _name = "work.center.assign.wizard"
    _description = "Assign a Document Within its Station"

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    allowed_user_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_allowed_user_ids",
        string="Responsible People",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assign To",
        required=True,
        domain="[('id', 'in', allowed_user_ids)]",
    )

    def _document(self):
        self.ensure_one()
        document = self.env[self.res_model].browse(self.res_id).exists()
        if not document:
            raise UserError(_("This document no longer exists."))
        return document

    @api.depends("res_model", "res_id")
    def _compute_allowed_user_ids(self):
        for wizard in self:
            users = self.env["res.users"]
            if wizard.res_model in self.env:
                station = wizard._document()._work_center_holding_station()
                if station and not station.is_unassigned:
                    users = station._responsible_users()[0]
            wizard.allowed_user_ids = users

    def action_assign(self):
        self.ensure_one()
        self._document()._work_center_manual_assign(self.user_id)
        return {"type": "ir.actions.act_window_close"}
