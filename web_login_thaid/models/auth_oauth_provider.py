# Copyright 2024 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests

from odoo import fields, models, tools


class AuthOauthProvider(models.Model):
    _inherit = "auth.oauth.provider"

    api_key = fields.Char(
        string="API Key",
        help="ThaiD requires this key as an HTTP header on token and JWKS requests.",
    )

    @tools.ormcache("self.jwks_uri", "self.api_key", "kid")
    def _get_keys(self, kid):
        headers = {}
        if self.api_key:
            headers["api_key"] = self.api_key
        r = requests.get(self.jwks_uri, headers=headers, timeout=10)
        r.raise_for_status()
        response = r.json()
        return [
            key
            for key in response["keys"]
            if kid is None or key.get("kid", None) == kid
        ]
