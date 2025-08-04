from odoo import api, fields, models


class ResUsersRole(models.Model):
    _inherit = "res.users.role"

    color = fields.Integer(
        string="Color",
        help="Color index for the role",
        default=0,
        store=True,
    )

    def write(self, vals):
        # Handle the color field specifically
        if 'color' in vals:
            color_val = vals.get('color')
            # Use the same sudo logic as the base module
            recs = self.sudo() if self._bypass_rules() else self
            return super(ResUsersRole, recs).write(vals)
        return super(ResUsersRole, self).write(vals)