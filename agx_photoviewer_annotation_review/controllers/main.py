from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class AnnotationReviewController(http.Controller):
    @http.route(
        "/agx_photoviewer_annotation_review/revise/<int:attachment_id>",
        type="http",
        auth="user",
        methods=["POST"],
    )
    def revise(self, attachment_id, ufile):
        """Upload ``ufile`` as the next Revision of the attachment."""
        try:
            revision = (
                request.env["ir.attachment"]
                .browse(attachment_id)
                ._annotation_create_revision(
                    ufile.filename, ufile.read(), ufile.content_type
                )
            )
        except (AccessError, UserError) as error:
            return request.make_json_response({"error": str(error)}, status=400)
        return request.make_json_response(
            {"id": revision.id, "name": revision.name, "mimetype": revision.mimetype}
        )
