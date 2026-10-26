from odoo import http
from odoo.http import content_disposition, request


class AnnotationController(http.Controller):
    @http.route(
        "/agx_photoviewer_annotation/export/<int:attachment_id>",
        type="http",
        auth="user",
    )
    def export(self, attachment_id):
        """Download the attachment with its annotation layer (never stored)."""
        Annotation = request.env["ir.attachment.annotation"]
        attachment = Annotation._get_readable_attachment(attachment_id)
        pdf = Annotation._export_pdf(attachment)
        filename = "%s (annotated).pdf" % (attachment.name or "file").rsplit(".", 1)[0]
        return request.make_response(
            pdf,
            headers=[
                ("Content-Type", "application/pdf"),
                ("Content-Length", len(pdf)),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )
