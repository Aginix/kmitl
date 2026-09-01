# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _is_role_gated(self):
        """Return True when this user should be shown the no-role landing.

        A user is gated when they have no role lines AND does not hold
        base.group_system (full Settings access). Only system administrators
        are exempt; IAM Managers without a role are gated like everyone else.
        Superuser context is always exempt.

        Uses sudo() to read role_line_ids because a gated user typically has
        no groups at all (base_user_role clears groups_id when role_line_ids
        is empty) and therefore cannot read the field under normal ACL.
        """
        if self.env.su:
            return False
        return not self.sudo().role_line_ids and not self.has_group(
            "base.group_system"
        )
