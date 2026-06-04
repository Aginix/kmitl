from odoo import SUPERUSER_ID, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _update_last_login(self):
        res = super()._update_last_login()
        self._revoke_access_if_no_employee()
        return res

    def _revoke_access_if_no_employee(self):
        """Internal users with no linked hr.employee have not been allocated
        permissions yet: strip all their groups so they see no apps until an
        admin provisions them. The main admin and superuser are exempt.

        Only internal users (members of base.group_user) are touched, so portal
        and public users — which legitimately have no employee — keep their
        access. This also makes the operation idempotent: a stripped user is no
        longer internal, so subsequent logins skip them.
        """
        internal = self.env.ref("base.group_user")
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        exempt_ids = {SUPERUSER_ID}
        if admin:
            exempt_ids.add(admin.id)
        for user in self:
            if user.id in exempt_ids:
                continue
            if user.employee_ids:
                continue
            if internal not in user.groups_id:
                # portal/public or already-stripped users: leave untouched
                continue
            user.sudo().write({"groups_id": [(5, 0, 0)]})
