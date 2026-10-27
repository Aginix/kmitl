# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request


class BudgetSupportRequestSarabunPreviewController(http.Controller):
    @http.route(
        ["/budget_support_request/<int:request_id>/sarabun_preview"],
        type="http",
        auth="user",
        website=False,
    )
    def budget_support_request_sarabun_preview(self, request_id, **kw):
        """Dry-run HTML of the หนังสือ the request would send."""
        support_request = request.env["budget.support.request"].browse(request_id)
        support_request.check_access_rights("read")
        support_request.check_access_rule("read")
        html = support_request._render_sarabun_draft_preview_html()
        return request.make_response(
            html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", len(html)),
            ],
        )
