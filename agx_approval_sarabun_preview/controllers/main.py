# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request


class ApprovalRequestSarabunPreviewController(http.Controller):
    @http.route(
        ["/approval/request/<int:request_id>/sarabun_preview"],
        type="http",
        auth="user",
        website=False,
    )
    def approval_request_sarabun_preview(self, request_id, **kw):
        """Dry-run HTML of the หนังสือ the request would send."""
        approval = request.env["approval.request"].browse(request_id)
        approval.check_access_rights("read")
        approval.check_access_rule("read")
        html = approval._render_sarabun_draft_preview_html()
        return request.make_response(
            html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", len(html)),
            ],
        )
