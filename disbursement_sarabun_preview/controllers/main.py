# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import request


class DisbursementSarabunPreviewController(http.Controller):
    @http.route(
        ["/disbursement/request/<int:request_id>/sarabun_preview"],
        type="http",
        auth="user",
        website=False,
    )
    def disbursement_sarabun_preview(self, request_id, **kw):
        """Dry-run HTML of the หนังสือ the request would send (ADR 0007)."""
        disbursement = request.env["disbursement.request"].browse(request_id)
        disbursement.check_access_rights("read")
        disbursement.check_access_rule("read")
        html = disbursement._render_sarabun_draft_preview_html()
        return request.make_response(
            html,
            headers=[
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", len(html)),
            ],
        )
