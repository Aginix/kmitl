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

    todo_subscribed_operating_unit_ids = fields.Many2many(
        "operating.unit",
        relation="mail_activity_todo_subscribed_ou_rel",
        column1="user_id",
        column2="operating_unit_id",
        string="Todo Subscribed Operating Units",
        help="Group Todos routed to any of these OUs land in your inbox. "
        "Empty = no group Todos.",
    )

    @api.depends("role_ids")
    def _compute_todo_role_ids(self):
        for user in self:
            user.todo_role_ids = user.sudo().role_ids.ids

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        for user in users:
            if not user.todo_subscribed_operating_unit_ids:
                user.todo_subscribed_operating_unit_ids = user.assigned_operating_unit_ids
        return users
