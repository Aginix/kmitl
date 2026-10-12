from odoo import api, models

from odoo.addons.website_profile.models.res_users import VALIDATION_KARMA_GAIN


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        # website_profile treats karma == 0 as "email not verified"; internal
        # users (LDAP first login, manual creation) never go through that flow.
        users.filtered(lambda u: not u.share and not u.karma).write(
            {"karma": VALIDATION_KARMA_GAIN}
        )
        return users
