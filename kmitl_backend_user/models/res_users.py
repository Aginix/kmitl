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

    def _get_contact_admin_action(self):
        return self.env.ref(
            "kmitl_backend_user.action_contact_admin", raise_if_not_found=False
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Send brand-new backend-UI-only users to the Contact-Admin page.

        Setting their Home Action means that, on login, they land on a friendly
        "contact your administrator" screen rather than a blank backend.
        """
        users = super().create(vals_list)
        action = self._get_contact_admin_action()
        group_user = self.env.ref("base.group_user", raise_if_not_found=False)
        backend_ui = self.env.ref(
            "base_group_backend.group_backend_ui_users", raise_if_not_found=False
        )
        if action and backend_ui:
            for user, vals in zip(users, vals_list):
                # Use "not in vals" to respect explicit action_id=False.
                # Check raw groups_id because base_group_backend hijacks
                # has_group("base.group_user") to return True for backend
                # users, so it cannot tell the two apart here.
                if (
                    "action_id" not in vals
                    and backend_ui in user.groups_id
                    and group_user not in user.groups_id
                ):
                    user.action_id = action.id
        return users

    def write(self, vals):
        res = super().write(vals)
        if "groups_id" in vals:
            action = self._get_contact_admin_action()
            group_user = self.env.ref(
                "base.group_user", raise_if_not_found=False
            )
            if action and group_user:
                promoted = self.filtered(
                    lambda u: u.action_id == action
                    and group_user in u.groups_id
                )
                if promoted:
                    promoted.sudo().write({"action_id": False})
        return res

    @api.model
    def get_access_admins(self):
        """Return a contact point for the Contact-Admin landing page.

        Uses ir.config_parameter ``kmitl_backend_user.contact_email`` when
        set; otherwise falls back to the names (no emails) of active system
        administrators so that a restricted user cannot harvest admin emails.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        contact_email = ICP.get_param("kmitl_backend_user.contact_email", "")
        if contact_email:
            return [{"name": "", "email": contact_email.strip()}]
        group = self.env.ref("base.group_system", raise_if_not_found=False)
        if not group:
            return []
        admins = group.sudo().users.filtered(
            lambda u: u.active and u.id != SUPERUSER_ID
        )
        return [{"name": u.name, "email": ""} for u in admins]
