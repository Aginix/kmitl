# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _is_provisioning_locked(self):
        """An internal, non-admin user that is not yet provisioned.

        Un-provisioned means the user is a plain internal user (``base.group_user``)
        with no linked ``hr.employee`` and no functional group beyond what every
        new user gets by default. Such users cannot reach any business app (the
        access layer already denies it), so on login they are sent to the
        "contact admin" landing page instead of an empty/confusing home.

        The check is intentionally "soft": as soon as HR links an employee *or*
        an admin grants any functional group, the user is no longer locked and
        lands normally — no group is ever stripped.
        """
        self.ensure_one()
        # Never lock the superuser or Settings admins.
        if self.id == SUPERUSER_ID or self._is_system():
            return False
        # Only internal users have backend access to gate in the first place.
        if not self.has_group("base.group_user"):
            return False
        # Provisioned the moment an employee is linked (any company).
        if self.sudo().employee_ids:
            return False
        # Respect admin override: any functional group beyond the default set
        # means the user has been deliberately granted access.
        default_user = self.env.ref("base.default_user", raise_if_not_found=False)
        if default_user:
            baseline = default_user.sudo().groups_id
        else:
            group_user = self.env.ref("base.group_user")
            baseline = group_user | group_user.trans_implied_ids
        return not (self.groups_id - baseline)
