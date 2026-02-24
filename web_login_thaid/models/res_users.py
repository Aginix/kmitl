# Copyright 2024 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import requests

from odoo import models
from odoo.exceptions import AccessDenied
from odoo.http import request


class ResUsers(models.Model):
    _inherit = "res.users"

    def _auth_oauth_signin(self, provider, validation, params):
        """Prevent auto-creation of users for providers that require api_key (ThaiD).
        Admin must pre-map oauth_uid on existing users.
        """
        oauth_provider = self.env["auth.oauth.provider"].browse(provider)
        if not oauth_provider.api_key:
            return super()._auth_oauth_signin(provider, validation, params)
        oauth_uid = validation["user_id"]
        oauth_user = self.search(
            [("oauth_uid", "=", oauth_uid), ("oauth_provider_id", "=", provider)]
        )
        if not oauth_user:
            raise AccessDenied()
        assert len(oauth_user) == 1
        oauth_user.write({"oauth_access_token": params["access_token"]})
        return oauth_user.login

    def _auth_oauth_get_tokens_auth_code_flow(self, oauth_provider, params):
        if not oauth_provider.api_key:
            return super()._auth_oauth_get_tokens_auth_code_flow(oauth_provider, params)
        code = params.get("code")
        auth = None
        if oauth_provider.client_secret:
            auth = (oauth_provider.client_id, oauth_provider.client_secret)
        response = requests.post(
            oauth_provider.token_endpoint,
            data=dict(
                client_id=oauth_provider.client_id,
                grant_type="authorization_code",
                code=code,
                code_verifier=oauth_provider.code_verifier,
                redirect_uri=request.httprequest.url_root + "auth_oauth/signin",
            ),
            headers={"api_key": oauth_provider.api_key},
            auth=auth,
            timeout=10,
        )
        response.raise_for_status()
        response_json = response.json()
        return response_json.get("access_token"), response_json.get("id_token")
