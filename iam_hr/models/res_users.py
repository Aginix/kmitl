# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, fields, models
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    iam_has_employee = fields.Boolean(
        string="Linked to Employee",
        compute="_compute_iam_has_employee",
        search="_search_iam_has_employee",
        help="Whether this user is linked to at least one employee record.",
    )

    def _compute_iam_has_employee(self):
        # sudo: an IAM manager may not have hr.employee read access; we only
        # expose the boolean, never employee data. One query for the whole set.
        linked = self.env["hr.employee"].sudo().search(
            [("user_id", "in", self.ids)]
        ).user_id
        for user in self:
            user.iam_has_employee = user in linked

    def _search_iam_has_employee(self, operator, value):
        if operator not in ("=", "!="):
            raise UserError(_("Unsupported operator for 'Linked to Employee'."))
        linked_user_ids = (
            self.env["hr.employee"]
            .sudo()
            .search([("user_id", "!=", False)])
            .user_id.ids
        )
        want_linked = (operator == "=") == bool(value)
        return [("id", "in" if want_linked else "not in", linked_user_ids)]
