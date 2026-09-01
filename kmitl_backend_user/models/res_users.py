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

    def _is_contact_admin_exempt(self):
        group_system = self.env.ref("base.group_system", raise_if_not_found=False)
        if not group_system:
            return self.browse()
        return self.filtered(lambda u: group_system in u.groups_id)

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        action = self._get_contact_admin_action()
        if action:
            for user, vals in zip(users, vals_list):
                if "action_id" not in vals and not user._is_contact_admin_exempt():
                    user.action_id = action.id
        return users

    def write(self, vals):
        res = super().write(vals)
        if "groups_id" in vals:
            action = self._get_contact_admin_action()
            if action:
                has_action = self.filtered(lambda u: u.action_id == action)
                exempt = has_action._is_contact_admin_exempt()
                if exempt:
                    exempt.sudo().write({"action_id": False})
                no_action = self.filtered(lambda u: not u.action_id)
                needs_action = no_action - no_action._is_contact_admin_exempt()
                if needs_action:
                    needs_action.sudo().write({"action_id": action.id})
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
