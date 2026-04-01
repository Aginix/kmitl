from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    profile_ids = fields.One2many("portal.profile", "partner_id", string="Profile")

    def _get_or_create_profile(self):
        self.ensure_one()
        profile = self.env["portal.profile"].search(
            [("partner_id", "=", self.id)], limit=1
        )
        if not profile:
            profile = self.env["portal.profile"].create({"partner_id": self.id})
        return profile

    def action_view_profile(self):
        self.ensure_one()
        profile = self._get_or_create_profile()
        return {
            "type": "ir.actions.act_window",
            "res_model": "portal.profile",
            "view_mode": "form",
            "res_id": profile.id,
            "target": "current",
        }
