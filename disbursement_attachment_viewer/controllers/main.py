# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import content_disposition, request


class DisbursementRequestController(http.Controller):
    @http.route(
        "/disbursement/request/<int:request_id>/attachments",
        type="http",
        auth="user",
    )
    def disbursement_request_attachments(self, request_id, **kwargs):
        dr = request.env["disbursement.request"].browse(request_id)
        if not dr.exists():
            return request.not_found()
        try:
            dr.check_access_rights("read")
            dr.check_access_rule("read")
        except AccessError:
            return request.make_response("Forbidden", status=403)

        pdf_content = dr._build_attachments_pdf()
        filename = "DR-%s-attachments.pdf" % (
            (dr.name or str(dr.id)).replace("/", "-"),
        )
        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf_content)),
            ("Content-Disposition", content_disposition(filename, disposition_type="inline")),
        ]
        return request.make_response(pdf_content, headers=headers)
