from odoo import api, models
from odoo.exceptions import AccessError


class IrAttachmentAnnotation(models.Model):
    _inherit = "ir.attachment.annotation"

    @api.model
    def _is_layer_locked(self, attachment):
        # Nobody annotates a superseded revision any more.
        return attachment.revision_superseded or super()._is_layer_locked(attachment)

    @api.model
    def annotation_load(self, attachment_id):
        result = super().annotation_load(attachment_id)
        attachment = self._get_readable_attachment(attachment_id)
        chain = attachment._revision_chain()
        latest = chain[-1]
        readable = self.env["ir.attachment"]
        for revision in chain:
            try:
                self.env["ir.attachment"].browse(revision.id).check("read")
            except AccessError:
                continue
            readable |= revision
        result.update(
            revisions=[
                {
                    "id": revision.id,
                    "name": revision.name,
                    "mimetype": revision.mimetype,
                    "number": revision.revision_number,
                    "latest": revision == latest,
                }
                for revision in readable
            ],
            superseded=attachment.revision_superseded,
            can_revise=self.env["ir.attachment"]
            .browse(attachment.id)
            ._annotation_can_revise(),
        )
        return result
