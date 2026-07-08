# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    iam_user_count = fields.Integer(
        string="# Users",
        compute="_compute_iam_user_count",
        help="Distinct backend users among this department's members.",
    )

    @api.depends("member_ids.user_id")
    def _compute_iam_user_count(self):
        # Read members as sudo: an IAM manager is not necessarily an HR officer
        # and has no read access on hr.employee. We only ever surface the count
        # and the resulting res.users -- never any employee data.
        for department in self:
            department.iam_user_count = len(department.sudo().member_ids.user_id)

    def action_iam_view_users(self):
        self.ensure_one()
        user_ids = self.sudo().member_ids.user_id.ids
        return {
            "name": _("Users"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "view_mode": "tree,form",
            "domain": [("id", "in", user_ids)],
            "context": {"create": False},
        }
