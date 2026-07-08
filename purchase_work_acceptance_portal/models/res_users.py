# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def review_user_count(self):
        """Hide work.acceptance from the tier-validation systray review list:
        committee review is surfaced through mail_activity_todo instead, so
        listing it here would double-count the same pending work.
        """
        result = super().review_user_count()
        return [r for r in result if r.get("model") != "work.acceptance"]
