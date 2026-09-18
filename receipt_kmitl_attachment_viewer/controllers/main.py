# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import content_disposition, request


class ReceiptRemittanceController(http.Controller):
    @http.route(
        "/receipt_kmitl/remittance/<int:remittance_id>/attachments",
        type="http",
        auth="user",
    )
    def remittance_attachments(self, remittance_id, **kwargs):
        remittance = request.env["kmitl.receipt.remittance"].browse(remittance_id)
        if not remittance.exists():
            return request.not_found()
        try:
            remittance.check_access_rights("read")
            remittance.check_access_rule("read")
        except AccessError:
            return request.make_response("Forbidden", status=403)

        pdf_content = remittance._build_attachments_pdf()
        filename = "RM-%s-%s-attachments.pdf" % (
            remittance._get_fy_be(),
            (remittance.name or str(remittance.id)).replace("/", "-"),
        )
        headers = [
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf_content)),
            ("Content-Disposition", content_disposition(filename, disposition_type="inline")),
        ]
        return request.make_response(pdf_content, headers=headers)
