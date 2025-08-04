from odoo import api, fields, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    color = fields.Integer(
        string="Color",
        help="Color index for the role",
        default=0,
        compute="_compute_color",
        inverse="_set_color",
        store=True,
    )
    color_stored = fields.Integer(
        string="Color Stored",
        default=0,
        store=True,
    )

    @api.depends('color_stored')
    def _compute_color(self):
        for record in self:
            record.color = record.color_stored

    def _set_color(self):
        for record in self:
            # Use sudo to ensure we can write
            record.sudo().color_stored = record.color