from odoo import fields, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    color = fields.Integer(
        string="Color",
        help="Color index for the role",
    )


class ResUsersRoleLine(models.Model):
    _inherit = "res.users.role.line"

    role_color = fields.Integer(
        string="Role Color",
        related="role_id.color",
        readonly=True,
        store=False,
    )