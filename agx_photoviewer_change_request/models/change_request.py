from odoo import fields, models


class ChangeRequest(models.Model):
    _inherit = "change.request"

    annotation_id = fields.Many2one(
        comodel_name="ir.attachment.annotation",
        string="Pin",
        index=True,
        ondelete="set null",
        help="The Comment pinning this request on a file.",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Pinned File",
        index=True,
        ondelete="set null",
        help="The revision of the file the request is pinned on.",
    )
    page = fields.Integer()
    file_name = fields.Char(
        help="Name of the pinned file, kept once the file is deleted."
    )

    def _format(self):
        result = super()._format()
        for values, request in zip(result, self):
            if not request.file_name:
                continue
            attachment = request.attachment_id
            values["pin"] = {
                "file_name": request.file_name,
                "page": request.page,
                "attachment_id": attachment.id,
                "annotation_id": request.annotation_id.id,
                "mimetype": attachment.mimetype or "",
                "revision_number": attachment["revision_number"]
                if "revision_number" in attachment._fields
                else 1,
            }
        return result

    def _update_request(self, text=None, assignees=None):
        super()._update_request(text=text, assignees=assignees)
        # The pin shows the request's text.
        if self.annotation_id and self.annotation_id.text != self.text:
            self.annotation_id.sudo().text = self.text

    def _delete_request(self):
        """Deleting a pinned request removes its pin, unless the Comment only
        stops asking for a fix (``change_request_keep_pin``)."""
        pins = self.sudo().annotation_id
        super()._delete_request()
        if not self.env.context.get("change_request_keep_pin"):
            pins.exists().unlink()
