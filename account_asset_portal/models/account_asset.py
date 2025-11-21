# -*- coding: utf-8 -*-
import random
import string

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


def _generate_random_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

class AccountAsset(models.Model):
    _name = "account.asset"
    _inherit = ["account.asset", "portal.mixin"]

    def _default_access_uid(self):
        return _generate_random_code(8)

    access_uid = fields.Char(
        string="Access Code",
        default=_default_access_uid,
        size=8,
        copy=False,
    )

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
        	rec.access_url = f"/account_assets/{self.access_uid}"

    def action_open_portal_view(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}{self.access_url}"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
        }
