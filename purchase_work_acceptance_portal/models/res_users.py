# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def review_user_count(self):
        """Exclude work.acceptance from the tier-validation systray — reviewers
        see it in the unified mail_activity_todo systray instead."""
        result = super().review_user_count()
        return [r for r in result if r.get("model") != "work.acceptance"]
