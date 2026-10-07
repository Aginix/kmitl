from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from ..pdf_export import build_annotated_pdf

# Values a client may set; the attachment, author and checksum are fixed.
EDITABLE_FIELDS = ("geometry", "color", "text")


class IrAttachmentAnnotation(models.Model):
    """One mark a user placed on one page of an attachment (ADR-0001).

    Users never touch this model directly (only system users have an ACL):
    the ``annotation_*`` methods below mirror ``ir.attachment.check`` —
    whoever can read the attachment sees and adds annotations — and only
    let the author change or remove theirs.
    """

    _name = "ir.attachment.annotation"
    _description = "Attachment Annotation"
    _order = "page, id"

    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    page = fields.Integer(required=True, default=1, help="1-based page number.")
    kind = fields.Selection(
        selection=[
            ("pen", "Pen"),
            ("check", "Check"),
            ("cross", "Cross"),
            ("highlight", "Highlight"),
            ("rect", "Rectangle"),
            ("comment", "Comment"),
        ],
        required=True,
    )
    geometry = fields.Json(
        required=True,
        help="Coordinates as fractions (0-1) of the page as displayed: "
        "pen {points: [[x, y], ...], width}, highlight/rect {x, y, w, h}, "
        "check/cross {x, y, size}, comment {x, y}. Widths and sizes are "
        "fractions of the page width.",
    )
    color = fields.Char(default="#e53935")
    text = fields.Text()
    checksum = fields.Char(
        readonly=True,
        help="Checksum of the attachment content the annotation was drawn on.",
    )

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    @api.model
    def _get_readable_attachment(self, attachment_id):
        attachment = self.env["ir.attachment"].browse(attachment_id).exists()
        if not attachment:
            raise UserError(_("This file no longer exists."))
        attachment.check("read")
        return attachment.sudo()

    def _check_author(self):
        for annotation in self:
            if annotation.create_uid != self.env.user:
                raise AccessError(_("You can only change your own annotations."))

    @api.model
    def _get_own_annotation(self, annotation_id):
        annotation = self.sudo().browse(annotation_id).exists()
        if not annotation:
            raise UserError(_("This annotation no longer exists."))
        self._get_readable_attachment(annotation.attachment_id.id)
        annotation._check_author()
        return annotation

    @api.model
    def _count_by_attachment(self, attachment_ids):
        ids = [aid for aid in attachment_ids if isinstance(aid, int)]
        if not ids:
            return {}
        groups = self.sudo()._read_group(
            [("attachment_id", "in", ids)], ["attachment_id"], ["attachment_id"]
        )
        return {
            group["attachment_id"][0]: group["attachment_id_count"] for group in groups
        }

    def _format(self):
        return [
            {
                "id": annotation.id,
                "page": annotation.page,
                "kind": annotation.kind,
                "geometry": annotation.geometry,
                "color": annotation.color,
                "text": annotation.text or "",
                "checksum": annotation.checksum,
                "author_id": annotation.create_uid.id,
                "author_name": annotation.create_uid.name,
                "create_date": fields.Datetime.to_string(annotation.create_date),
                "is_own": annotation.create_uid == self.env.user,
            }
            for annotation in self
        ]

    # ------------------------------------------------------------------
    # RPC used by the photo viewer
    # ------------------------------------------------------------------

    @api.model
    def annotation_load(self, attachment_id):
        attachment = self._get_readable_attachment(attachment_id)
        annotations = self.sudo().search([("attachment_id", "=", attachment.id)])
        return {
            "checksum": attachment.checksum,
            "annotations": annotations._format(),
        }

    @api.model
    def annotation_save(self, vals):
        """Create an annotation, or update one of the user's own (``vals['id']``)."""
        values = {key: vals[key] for key in EDITABLE_FIELDS if key in vals}
        if vals.get("id"):
            annotation = self._get_own_annotation(vals["id"])
            annotation.write(values)
        else:
            attachment = self._get_readable_attachment(vals.get("attachment_id"))
            values.update(
                attachment_id=attachment.id,
                page=vals.get("page") or 1,
                kind=vals.get("kind"),
                checksum=attachment.checksum,
            )
            # Created as the user (sudo keeps the uid) so create_uid is the author.
            annotation = self.sudo().create(values)
        return annotation._format()[0]

    @api.model
    def annotation_delete(self, annotation_id):
        self._get_own_annotation(annotation_id).unlink()
        return True

    @api.model
    def annotation_counts(self, attachment_ids):
        attachments = self.env["ir.attachment"].browse(attachment_ids).exists()
        attachments.check("read")
        return self._count_by_attachment(attachments.ids)

    @api.model
    def annotation_session_note(self, attachment_id, counts, comment_ids=()):
        """Post one internal note summarising what the user did on the file.

        Skipped when the attachment is not linked to a record that has a
        chatter (e.g. a many2many_binary upload with res_id 0).
        """
        attachment = self._get_readable_attachment(attachment_id)
        if not (attachment.res_model and attachment.res_id):
            return False
        Model = self.env.get(attachment.res_model)
        if Model is None or not hasattr(Model, "message_post"):
            return False
        record = Model.sudo().browse(attachment.res_id).exists()
        if not record:
            return False
        labels = [
            (counts.get("added"), _("added %s")),
            (counts.get("changed"), _("changed %s")),
            (counts.get("removed"), _("removed %s")),
        ]
        summary = ", ".join(label % count for count, label in labels if count)
        if not summary:
            return False
        comments = self.sudo().search(
            [
                ("id", "in", list(comment_ids)),
                ("attachment_id", "=", attachment.id),
                ("kind", "=", "comment"),
                ("create_uid", "=", self.env.uid),
            ]
        )
        body = Markup("<p>%s</p>") % _(
            "Annotations on %(file)s: %(summary)s",
            file=attachment.name or "",
            summary=summary,
        )
        if comments:
            body += Markup("<ul>%s</ul>") % Markup("").join(
                Markup("<li>%s</li>")
                % _("Page %(page)s: %(text)s", page=comment.page, text=comment.text)
                for comment in comments
            )
        record.message_post(
            body=body,
            subtype_xmlid="mail.mt_note",
            author_id=self.env.user.partner_id.id,
        )
        return True

    # ------------------------------------------------------------------
    # Annotated export
    # ------------------------------------------------------------------

    @api.model
    def _export_pdf(self, attachment):
        """Return the annotated export of ``attachment`` as PDF bytes."""
        annotations = self.sudo().search([("attachment_id", "=", attachment.id)])
        mimetype = attachment.mimetype or ""
        if mimetype != "application/pdf" and (
            not mimetype.startswith("image/") or mimetype == "image/svg+xml"
        ):
            raise UserError(_("Only images and PDF files can be exported."))
        comments = []
        for annotation in annotations.filtered(lambda a: a.kind == "comment"):
            date = fields.Datetime.context_timestamp(self, annotation.create_date)
            comments.append(
                {
                    "id": annotation.id,
                    "page": annotation.page,
                    "author": annotation.create_uid.name,
                    "date": date.strftime("%d/%m/%Y %H:%M"),
                    "text": annotation.text or "",
                }
            )
        return build_annotated_pdf(
            attachment.raw,
            is_pdf=mimetype == "application/pdf",
            annotations=[
                {
                    "id": annotation.id,
                    "page": annotation.page,
                    "kind": annotation.kind,
                    "geometry": annotation.geometry or {},
                    "color": annotation.color,
                }
                for annotation in annotations
            ],
            comments=comments,
            title=_("Comments on %s", attachment.name or ""),
            page_label=_("Page"),
        )
