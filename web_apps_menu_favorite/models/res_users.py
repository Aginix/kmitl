from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    favorite_menu_ids = fields.Many2many(
        "ir.ui.menu",
        "web_apps_menu_favorite_rel",
        "user_id",
        "menu_id",
        string="Favorite Apps",
        help="Apps this user pinned to the top of their Apps grid.",
    )
