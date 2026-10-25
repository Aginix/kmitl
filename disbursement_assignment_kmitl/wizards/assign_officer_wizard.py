# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models

OFFICER_GROUP = "disbursement.group_disbursement_officer"


class DisbursementAssignOfficerWizard(models.TransientModel):
    # Dedicated name (not the procurement ``assign.officer.wizard``): reusing
    # that name would make this an implicit cross-module inherit of a model we
    # do not depend on.
    _name = "disbursement.assign.officer.wizard"
    _description = "Assign Responsible Officer"

    request_id = fields.Many2one(
        "disbursement.request",
        string="Disbursement Request",
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Assigned Officer",
        required=True,
        domain="[('id', 'in', allowed_user_ids)]",
    )
    allowed_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_allowed_user_ids",
    )

    @api.depends("request_id")
    def _compute_allowed_user_ids(self):
        """The people of the station holding the request."""
        group = self.env.ref(OFFICER_GROUP, raise_if_not_found=False)
        officers = group.users if group else self.env["res.users"]
        for wiz in self:
            station = (
                wiz.request_id._work_center_holding_station()
                if wiz.request_id
                else False
            )
            wiz.allowed_user_ids = (
                station._responsible_users()[0] if station else officers
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if res.get("request_id") and "user_id" in fields_list:
            request = self.env["disbursement.request"].browse(res["request_id"])
            if request.assigned_to:
                res["user_id"] = request.assigned_to.id
        return res

    def action_assign(self):
        self.ensure_one()
        request = self.request_id
        request._work_center_check_move()
        old_officer = request.assigned_to
        request.assigned_to = self.user_id
        if old_officer and old_officer != self.user_id:
            request._assignment_clear_activity(old_officer)
        if self.user_id and self.user_id != self.env.user:
            request._assignment_notify(self.user_id)
        return {"type": "ir.actions.act_window_close"}
