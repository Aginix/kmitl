import base64

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

# Longest chain of revisions followed, against a corrupted (cyclic) chain.
MAX_REVISIONS = 100


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    revision_previous_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Previous Revision",
        index=True,
        ondelete="set null",
        copy=False,
    )
    revision_number = fields.Integer(default=1, copy=False)
    revision_superseded = fields.Boolean(
        index=True,
        copy=False,
        help="A later revision of this file was uploaded (ADR-0003).",
    )

    def _attachment_format(self, legacy=False):
        # A chatter message keeps the revision it was posted with: it is shown
        # as superseded, and left out of the record's files.
        res_list = super()._attachment_format(legacy=legacy)
        superseded = {
            attachment.id: attachment._revision_chain()[-1].revision_number
            for attachment in self
            if attachment.revision_superseded
        }
        for res in res_list:
            if res["id"] in superseded:
                res["revisionSupersededBy"] = superseded[res["id"]]
        return res_list

    # ------------------------------------------------------------------
    # Revisions
    # ------------------------------------------------------------------

    def _revision_chain(self):
        """Every revision of this file, oldest first (sudo)."""
        self.ensure_one()
        first = self.sudo()
        for _step in range(MAX_REVISIONS):
            if not first.revision_previous_id:
                break
            first = first.revision_previous_id
        chain = first
        for _step in range(MAX_REVISIONS):
            following = self.sudo().search(
                [("revision_previous_id", "=", chain[-1].id)], limit=1
            )
            if not following or following in chain:
                break
            chain |= following
        return chain

    def write(self, vals):
        if "raw" in vals or "datas" in vals:
            self._check_annotated_content_kept(vals)
        return super().write(vals)

    def _check_annotated_content_kept(self, vals):
        """An annotated file is never overwritten: changing it means uploading
        a revision (ADR-0003). Rewriting the same content (e.g. moving it to
        another storage) is fine."""
        counts = self.env["ir.attachment.annotation"]._count_by_attachment(self.ids)
        annotated = self.filtered(lambda attachment: counts.get(attachment.id))
        if not annotated:
            return
        raw = vals["raw"] if "raw" in vals else base64.b64decode(vals["datas"] or b"")
        if isinstance(raw, str):
            raw = raw.encode()
        checksum = self._compute_checksum(raw or b"")
        if any(attachment.checksum != checksum for attachment in annotated):
            raise UserError(
                _(
                    "This file carries annotations and cannot be replaced: "
                    "upload a revision of it instead."
                )
            )

    def _annotation_can_revise(self):
        """Whether the user may upload a revision of this attachment."""
        self.ensure_one()
        try:
            self._annotation_check_revise()
        except (AccessError, UserError):
            return False
        return True

    def _annotation_check_revise(self):
        """Raise unless the user may upload a revision of this attachment:
        it is the latest one and the user may edit the record it belongs to,
        as for attaching any file."""
        self.ensure_one()
        Annotation = self.env["ir.attachment.annotation"]
        attachment = Annotation._get_readable_attachment(self.id)
        if attachment.revision_superseded:
            raise UserError(_("Only the latest revision of a file can be revised."))
        holder = Annotation._get_holder_record(attachment)
        if holder:
            record = self.env[holder._name].browse(holder.id)
            record.check_access_rights("write")
            record.check_access_rule("write")
        else:
            self.check("write")
        return attachment, holder

    def _annotation_create_revision(self, name, raw, mimetype=None):
        """Upload ``raw`` as the next revision of this attachment and return
        it; it replaces this one on the record (ADR-0003)."""
        previous, holder = self._annotation_check_revise()
        mimetype = self._compute_mimetype(
            {"name": name, "raw": raw, "mimetype": mimetype}
        )
        # SVG is stored as text/plain for most users (ir.attachment._check_contents).
        if mimetype != "application/pdf" and (
            not mimetype.startswith("image/") or mimetype == "image/svg+xml"
        ):
            raise UserError(_("A revision must be an image or a PDF file."))
        # A file uploaded before its record was saved (res_id 0) is tied to
        # the record from now on, its revisions too.
        res_model = holder._name if holder else previous.res_model
        res_id = holder.id if holder else previous.res_id
        # Created as the user (sudo keeps the uid): create_uid is the uploader.
        revision = self.sudo().create(
            {
                "name": name or previous.name,
                "raw": raw,
                "mimetype": mimetype,
                "res_model": res_model,
                "res_id": res_id,
                "revision_previous_id": previous.id,
                "revision_number": previous.revision_number + 1,
            }
        )
        previous.write(
            {"revision_superseded": True, "res_model": res_model, "res_id": res_id}
        )
        if holder:
            holder._annotation_replace_revision(previous, revision)
        return revision
