# -*- coding: utf-8 -*-
import random
import string

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


def _generate_random_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

class AccountAsset(models.Model):
    _inherit = 'account.asset'

    def _default_access_uid(self):
        return _generate_random_code(8)

    access_uid = fields.Char(
        string="Access Code",
        default=_default_access_uid,
        size=8,
        copy=False,
    )

    def action_open_portal_view(self):
        self.ensure_one()

        if not self.access_uid:
            raise UserError("Access code is missing.")
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}/account_assets/{self.access_uid}"

        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
        }
