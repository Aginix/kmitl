# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import werkzeug.utils

from odoo import models
from odoo.http import request

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
    "/iam/no-role",
    "/iam/check-role",
)

_LANDING_REDIRECT = "/iam/no-role"


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _pre_dispatch(cls, rule, arguments):
        response = super()._pre_dispatch(rule, arguments)
        if response is not None:
            return response

        uid = request.session.uid
        if not uid:
            return None

        content_type = request.httprequest.content_type or ""
        if "application/json" in content_type:
            return None

        path = request.httprequest.path
        if any(path.startswith(prefix) for prefix in _WHITELIST_PREFIXES):
            return None

        user = request.env["res.users"].sudo().browse(uid)
        if user._is_role_gated():
            return werkzeug.utils.redirect(_LANDING_REDIRECT)

        return None
