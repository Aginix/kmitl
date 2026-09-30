# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import os

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import content_disposition, request


class AttachmentCarouselController(http.Controller):
    @http.route(
        "/attachment_carousel/preview/<int:attachment_id>",
        type="http",
        auth="user",
    )
    def preview(self, attachment_id, **kwargs):
        """Return the attachment as a PDF for inline preview.

        - PDF attachment → its own bytes.
        - Office attachment → LibreOffice-converted PDF (cached on the record).
        - Anything else → 404 (the frontend should render a download-link
          fallback instead of calling this route).
        """
        attachment = request.env["ir.attachment"].browse(attachment_id).exists()
        if not attachment:
            return request.not_found()
        try:
            attachment.check_access_rights("read")
            attachment.check_access_rule("read")
        except AccessError:
            return request.not_found()
        try:
            pdf_bytes = attachment.get_preview_pdf()
        except UserError as e:
            return request.make_response(
                str(e), headers=[("Content-Type", "text/plain")], status=415
            )
        if not pdf_bytes:
            return request.not_found()
        base_name = os.path.splitext(attachment.name or "preview")[0] or "preview"
        return request.make_response(
            pdf_bytes,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", str(len(pdf_bytes))),
                (
                    "Content-Disposition",
                    content_disposition(
                        "%s.pdf" % base_name, disposition_type="inline"
                    ),
                ),
            ],
        )
