# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.http import content_disposition, request


class DisbursementSarabunPreviewController(http.Controller):
    @http.route(
        ["/disbursement/request/<int:request_id>/sarabun_preview"],
        type="http",
        auth="user",
        website=False,
    )
    def disbursement_sarabun_preview(self, request_id, **kw):
        """PDF of the หนังสือ the request sends (ADR 0007): the live one once
        sent to Sarabun, else a dry run."""
        disbursement = request.env["disbursement.request"].browse(request_id)
        disbursement.check_access_rights("read")
        disbursement.check_access_rule("read")
        pdf, filename = disbursement._get_sarabun_preview_pdf()
        return request.make_response(
            pdf,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
                ("Content-Disposition", content_disposition(filename, "inline")),
            ],
        )
