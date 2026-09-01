# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _is_role_gated(self):
        """Return True when this user should be shown the no-role landing.

        A user is gated when they have no role lines AND do not hold
        base.group_erp_manager (which covers IAM Managers, full Settings
        admins, and any other elevated group that implies erp_manager).
        Superuser context is always exempt.
        """
        if self.env.su:
            return False
        return not self.role_line_ids and not self.has_group(
            "base.group_erp_manager"
        )

    def _get_home_action(self):
        if self._is_role_gated():
            return self.env.ref("iam_no_role_landing.action_no_role_landing")
        return super()._get_home_action()

    @api.model
    def get_no_role_landing_info(self):
        """Return landing page content for the current user."""
        ICP = self.env["ir.config_parameter"].sudo()
        contact_message = ICP.get_param(
            "iam_no_role_landing.contact_message",
            default="กรุณาติดต่อผู้ดูแลระบบ (IAM Manager) เพื่อขอกำหนดสิทธิ์การใช้งาน",
        )
        return {
            "contact_message": contact_message,
            "user_name": self.env.user.name,
        }

    @api.model
    def check_role_status(self):
        """Check whether the current user still has no role."""
        return {"has_role": not self.env.user._is_role_gated()}
