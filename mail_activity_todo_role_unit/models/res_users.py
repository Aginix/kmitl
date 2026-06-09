from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    todo_role_ids = fields.Many2many(
        "res.users.role",
        compute="_compute_todo_role_ids",
        compute_sudo=True,
        string="Todo Roles",
        help="Roles the user holds, exposed without ERP-manager rights so Todo "
        "routing (inbox domain + record rules) can read them.",
    )

    @api.depends("role_ids")
    def _compute_todo_role_ids(self):
        for user in self:
            user.todo_role_ids = user.sudo().role_ids.ids
