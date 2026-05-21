from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _update_last_login(self):
        res = super()._update_last_login()
        self._link_applicants_to_partner()
        return res

    def _link_applicants_to_partner(self):
        """On login, link any unowned applicants whose email_from matches the
        user's partner email. Runs once per session; idempotent."""
        partner = self.partner_id
        if not partner.email:
            return
        self.env["hr.applicant"].sudo().search(
            [
                ("partner_id", "=", False),
                ("email_from", "=ilike", partner.email),
            ]
        ).write({"partner_id": partner.id})
