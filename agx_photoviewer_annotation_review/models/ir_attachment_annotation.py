from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class IrAttachmentAnnotation(models.Model):
    _inherit = "ir.attachment.annotation"

    change_request = fields.Boolean(
        copy=False,
        help="A Comment asking the maker to fix or explain something.",
    )
    request_state = fields.Selection(
        selection=[("open", "Open"), ("answered", "Answered"), ("closed", "Closed")],
        copy=False,
    )
    response = fields.Text(copy=False)
    response_uid = fields.Many2one(
        comodel_name="res.users", string="Responded by", copy=False
    )
    response_date = fields.Datetime(string="Responded on", copy=False)

    @api.constrains("kind", "change_request")
    def _check_change_request_kind(self):
        if any(a.change_request and a.kind != "comment" for a in self):
            raise ValidationError(_("Only a comment can be a change request."))

    # ------------------------------------------------------------------
    # Locks
    # ------------------------------------------------------------------

    @api.model
    def _is_record_locked(self, attachment):
        """Whether the record the file belongs to locked its layer: Change
        requests are then frozen too."""
        record = self._get_holder_record(attachment)
        return bool(record) and record._annotation_is_locked()

    @api.model
    def _is_layer_locked(self, attachment):
        # Nobody annotates a superseded revision any more.
        return attachment.revision_superseded or super()._is_layer_locked(attachment)

    # ------------------------------------------------------------------
    # Format
    # ------------------------------------------------------------------

    def _format(self):
        result = super()._format()
        for values, annotation in zip(result, self):
            values.update(
                attachment_id=annotation.attachment_id.id,
                revision_number=annotation.attachment_id.revision_number,
                change_request=annotation.change_request,
                request_state=annotation.request_state or False,
                response=annotation.response or "",
                response_name=annotation.response_uid.name or "",
                response_date=fields.Datetime.to_string(annotation.response_date)
                if annotation.response_date
                else False,
            )
        return result

    # ------------------------------------------------------------------
    # RPC used by the photo viewer
    # ------------------------------------------------------------------

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
        requests = self.sudo().search(
            [
                ("attachment_id", "in", readable.ids),
                ("change_request", "=", True),
                ("request_state", "!=", "closed"),
            ],
            order="attachment_id, page, id",
        )
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
            record_locked=self._is_record_locked(attachment),
            can_revise=self.env["ir.attachment"]
            .browse(attachment.id)
            ._annotation_can_revise(),
            requests=requests._format(),
        )
        return result

    @api.model
    def annotation_save(self, vals):
        """Also sets whether a Comment is a Change request
        (``vals['change_request']``), only on the user's own Comments."""
        result = super().annotation_save(vals)
        if "change_request" in vals:
            annotation = self.sudo().browse(result["id"])
            flag = bool(vals["change_request"]) and annotation.kind == "comment"
            if flag != annotation.change_request:
                annotation.write(
                    {
                        "change_request": flag,
                        "request_state": "open" if flag else False,
                        "response": False,
                        "response_uid": False,
                        "response_date": False,
                    }
                )
            result = annotation._format()[0]
        return result

    @api.model
    def _get_change_request(self, annotation_id):
        annotation = self.sudo().browse(annotation_id).exists()
        if not (annotation and annotation.change_request):
            raise UserError(_("This change request no longer exists."))
        self._get_readable_attachment(annotation.attachment_id.id)
        # A superseded revision still has its requests answered and closed;
        # a record that locked its layer froze them.
        if self._is_record_locked(annotation.attachment_id):
            raise UserError(_("Annotations on this file are locked."))
        return annotation

    @api.model
    def annotation_respond(self, annotation_id, response):
        """Answer a Change request: anyone who reads the file but its author."""
        annotation = self._get_change_request(annotation_id)
        if annotation.create_uid == self.env.user:
            raise AccessError(_("You cannot answer your own change request."))
        if annotation.request_state == "closed":
            raise UserError(_("This change request is closed."))
        response = (response or "").strip()
        if not response:
            raise UserError(_("Write a response first."))
        annotation.write(
            {
                "response": response,
                "response_uid": self.env.uid,
                "response_date": fields.Datetime.now(),
                "request_state": "answered",
            }
        )
        return annotation._format()[0]

    @api.model
    def annotation_set_request_state(self, annotation_id, state):
        """Close or reopen a Change request: its author only."""
        if state not in ("open", "closed"):
            raise UserError(_("A change request can only be closed or reopened."))
        annotation = self._get_change_request(annotation_id)
        annotation._check_author()
        annotation.request_state = state
        return annotation._format()[0]

    # ------------------------------------------------------------------
    # Session note
    # ------------------------------------------------------------------

    def _session_note_comment_line(self):
        line = super()._session_note_comment_line()
        if self.change_request:
            return _("[Change request] %s", line)
        return line

    @api.model
    def _session_note_extra(self, attachment):
        extra = super()._session_note_extra(attachment)
        count = attachment.open_request_count
        if count:
            extra += Markup("<p>%s</p>") % _(
                "Change requests still open on this file: %s", count
            )
        return extra
