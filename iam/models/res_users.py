# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import _, api, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.constrains("groups_id")
    def _check_iam_no_system_escalation(self):
        """Keep the one privilege boundary the IAM app intentionally closes.

        A delegated IAM manager (``iam.group_iam_manager``, which implies
        ``base.group_erp_manager``) can administer every user, role, group,
        access right and record rule -- but must never be able to *mint a new
        full Settings administrator*. Only an existing ``base.group_system``
        admin may grant that group.

        We check the resulting state (``group_system`` present on a user)
        rather than the write payload, so this also covers the indirect paths:
        granting a group/role that *implies* ``group_system`` (implied groups
        are materialised into ``groups_id`` at write time) and adding a user
        through ``res.groups.users``.
        """
        # Bypass for superuser / internal data loads and for genuine admins.
        if self.env.su or self.env.user.has_group("base.group_system"):
            return
        system_group = self.env.ref("base.group_system", raise_if_not_found=False)
        if not system_group:
            return
        for user in self:
            if system_group in user.groups_id:
                raise ValidationError(
                    _(
                        "You are not allowed to grant Settings / Administration "
                        "access. Only a full system administrator can create "
                        "another system administrator."
                    )
                )
