from odoo import api, fields, models


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    favorite_user_ids = fields.Many2many(
        "res.users",
        "approval_category_favorite_user_rel",
        "category_id",
        "user_id",
        string="Favorited By",
    )
    is_favorite = fields.Boolean(
        compute="_compute_is_favorite", compute_sudo=True, string="Favorite"
    )

    @api.depends("favorite_user_ids")
    @api.depends_context("uid")
    def _compute_is_favorite(self):
        for category in self:
            category.is_favorite = self.env.user in category.favorite_user_ids

    def toggle_favorite(self):
        self.ensure_one()
        if self.env.user in self.favorite_user_ids:
            self.sudo().write({"favorite_user_ids": [(3, self.env.uid)]})
            return False
        self.sudo().write({"favorite_user_ids": [(4, self.env.uid)]})
        return True
