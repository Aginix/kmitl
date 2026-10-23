from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class AnnotationRevisionController(http.Controller):
    @http.route(
        "/agx_photoviewer_annotation_revision/revise/<int:attachment_id>",
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
            {
                "id": revision.id,
                "name": revision.name,
                "mimetype": revision.mimetype,
                "res_model": revision.res_model,
                "res_id": revision.res_id,
                "previous_id": attachment_id,
                "number": revision.revision_number,
            }
        )
