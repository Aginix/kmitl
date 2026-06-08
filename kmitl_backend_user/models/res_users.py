# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import SUPERUSER_ID, api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _default_groups(self):
        """Default new users to the restricted "Backend UI user" type.

        Instead of "Internal User" (``base.group_user``), which grants a lot of
        implicit access, a freshly created user becomes a
        ``base_group_backend.group_backend_ui_users`` user: it can reach the
        backend but sees no application until an admin grants one. We only swap
        that single User-Type group and keep any other technical defaults the
        template user carries. This changes the *default* for new users only;
        existing users are untouched (we never write to ``base.default_user``).
        """
        groups = super()._default_groups()
        group_user = self.env.ref("base.group_user", raise_if_not_found=False)
        backend_ui = self.env.ref(
            "base_group_backend.group_backend_ui_users", raise_if_not_found=False
        )
        if backend_ui and group_user and group_user in groups:
            groups = (groups - group_user) | backend_ui
        return groups

    @api.model_create_multi
    def create(self, vals_list):
        """Send brand-new backend-UI-only users to the Contact-Admin page.

        Setting their Home Action means that, on login, they land on a friendly
        "contact your administrator" screen rather than a blank backend.
        """
        users = super().create(vals_list)
        action = self.env.ref(
            "kmitl_backend_user.action_contact_admin", raise_if_not_found=False
        )
        group_user = self.env.ref("base.group_user", raise_if_not_found=False)
        backend_ui = self.env.ref(
            "base_group_backend.group_backend_ui_users", raise_if_not_found=False
        )
        if action and backend_ui:
            for user, vals in zip(users, vals_list):
                # Check the raw groups: base_group_backend hijacks
                # has_group("base.group_user") to also return True for backend
                # users, so it cannot tell the two apart here.
                if (
                    not vals.get("action_id")
                    and backend_ui in user.groups_id
                    and group_user not in user.groups_id
                ):
                    user.action_id = action.id
        return users

    @api.model
    def get_access_admins(self):
        """Return active system administrators' contact info for the
        Contact-Admin landing page.

        Runs sudo so a restricted backend-UI user (who cannot read other users)
        can still see who to contact.
        """
        group = self.env.ref("base.group_system", raise_if_not_found=False)
        if not group:
            return []
        admins = group.sudo().users.filtered(
            lambda u: u.active and u.email and u.id != SUPERUSER_ID
        )
        return [{"name": u.name, "email": u.email} for u in admins]
