from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.agx_change_request.models.change_request_mixin import OUTSTANDING


class IrAttachmentAnnotation(models.Model):
    _inherit = "ir.attachment.annotation"

    def _get_pin_requests(self):
        """The Change requests these Comments pin (sudo)."""
        return (
            self.env["change.request"]
            .sudo()
            .search([("annotation_id", "in", self.ids)])
        )

    @api.model
    def _get_request_record(self, attachment):
        """The record ``attachment`` belongs to when it takes Change requests
        and the user reads it (as the user), else an empty recordset."""
        record = self._get_holder_record(attachment)
        if not record or "change_request_count" not in record._fields:
            return self.env["base"]
        try:
            return self.env["change.request"]._get_readable_record(
                record._name, record.id
            )
        except (AccessError, UserError):
            return self.env["base"]

    def _format(self):
        result = super()._format()
        requests = {
            request.annotation_id.id: request for request in self._get_pin_requests()
        }
        for values, annotation in zip(result, self):
            request = requests.get(annotation.id)
            values["change_request"] = bool(request)
            values["request"] = request._format()[0] if request else False
        return result

    # ------------------------------------------------------------------
    # RPC used by the photo viewer
    # ------------------------------------------------------------------

    @api.model
    def annotation_load(self, attachment_id):
        result = super().annotation_load(attachment_id)
        attachment = self._get_readable_attachment(attachment_id)
        record = self._get_request_record(attachment)
        result["can_request"] = bool(record) and not self._is_layer_locked(attachment)
        result["requests"] = []
        result["assignee_suggestions"] = []
        if record:
            Request = self.env["change.request"]
            result["requests"] = (
                Request.sudo()
                .search(
                    [
                        ("attachment_id", "in", attachment._request_files().ids),
                        ("state", "in", OUTSTANDING),
                    ]
                )
                ._format()
            )
            result["assignee_suggestions"] = Request._assignee_suggestions(record)
        return result

    @api.model
    def annotation_save(self, vals):
        """Also makes a Comment the pin of a Change request
        (``vals['change_request']``, with ``vals['assignee_ids']``), or stops
        it being one; only on the user's own Comments."""
        flag = vals.get("change_request")
        assignee_ids = vals.get("assignee_ids")
        result = super().annotation_save(vals)
        annotation = self.sudo().browse(result["id"])
        if annotation.kind != "comment" or (flag is None and assignee_ids is None):
            if "text" in vals:
                request = annotation._get_pin_requests()
                if request:
                    request._update_request(text=annotation.text)
            return annotation._format()[0]
        Request = self.env["change.request"]
        request = annotation._get_pin_requests()
        assignees = None
        if assignee_ids is not None:
            assignees = self.env["res.users"].browse(list(assignee_ids)).exists()
        if flag and not request:
            record = self._get_request_record(annotation.attachment_id)
            if not record:
                raise UserError(
                    _("The files of this document take no change requests.")
                )
            attachment = annotation.attachment_id
            Request._create_request(
                record,
                annotation.text,
                assignees,
                values={
                    "annotation_id": annotation.id,
                    "attachment_id": attachment.id,
                    "page": annotation.page,
                    "file_name": attachment.name or "",
                },
            )
        elif flag is False and request:
            request.with_context(change_request_keep_pin=True)._delete_request()
        elif request:
            request._update_request(
                text=annotation.text if "text" in vals else None, assignees=assignees
            )
        return annotation._format()[0]

    @api.model
    def annotation_delete(self, annotation_id):
        """Removing the pin of a Change request deletes the request."""
        annotation = self._get_own_annotation(annotation_id)
        request = annotation._get_pin_requests()
        if not request:
            return super().annotation_delete(annotation_id)
        self._check_layer_open(annotation.attachment_id)
        request._delete_request()
        return True

    @api.model
    def annotation_session_note(self, attachment_id, counts, comment_ids=()):
        # Change requests are not in it: each of their steps is posted on its own.
        pins = self.sudo().browse(list(comment_ids))._get_pin_requests().annotation_id
        comment_ids = [i for i in comment_ids if i not in pins.ids]
        return super().annotation_session_note(attachment_id, counts, comment_ids)
