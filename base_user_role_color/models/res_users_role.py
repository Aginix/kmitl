from odoo import fields, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    color = fields.Integer(
        string="Color",
        help="Color index for the role",
        default=0,
    )