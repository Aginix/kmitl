# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import werkzeug.utils

from odoo import models
from odoo.http import request


# Paths that a gated user must always be able to reach. Anything NOT in this
# list and NOT a JSON-RPC call will be redirected to the landing action.
_WHITELIST_PREFIXES = (
    "/web/login",
    "/web/session/logout",
    "/web/session/destroy",
    "/web/session/authenticate",
    "/web/static/",
    "/web/assets/",
    "/web/image/",
    "/web/binary/",
    "/web/webclient/",
    "/web/favicon.ico",
    "/longpolling/",
    "/websocket",
    # Landing action URL (new-style /odoo/ router)
    "/odoo/action-iam_no_role_landing",
)

_LANDING_REDIRECT = "/odoo/action-iam_no_role_landing.action_no_role_landing"


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _pre_dispatch(cls, rule, arguments):
        """Redirect gated users away from any protected backend route."""
        response = super()._pre_dispatch(rule, arguments)
        if response is not None:
            return response

        # Only act on authenticated backend sessions.
        uid = request.session.uid
        if not uid:
            return None

        # JSON-RPC (XHR) calls must pass through — the OWL component itself
        # issues RPC calls (get_no_role_landing_info, check_role_status) and
        # Odoo's own group ACL is the data guard for every other endpoint.
        content_type = request.httprequest.content_type or ""
        if "application/json" in content_type:
            return None

        path = request.httprequest.path
        if any(path.startswith(prefix) for prefix in _WHITELIST_PREFIXES):
            return None

        user = request.env["res.users"].browse(uid)
        if user._is_role_gated():
            return werkzeug.utils.redirect(_LANDING_REDIRECT)

        return None
