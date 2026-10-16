"""Regenerate the frozen ฉบับลงนาม of a completed หนังสือ (ADR-0019).

The signed copy is frozen once at completion and never re-rendered. When a
correction lands after that (e.g. a signer's ตำแหน่ง fixed by
``agx_sarabun_route_edit_person_capacity``), a Sarabun Manager re-renders it from the
current data: the frozen PDF and its visible attachment copy are REPLACED (the old
one is deleted) through the core ``_freeze_signed_copy``, keeping the original
freeze time (``signed_at``). Not logged to the chatter — only managers may do it.
"""

from odoo import _, models
from odoo.exceptions import UserError


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    def action_regenerate_signed_pdf(self):
        self.ensure_one()
        if not self.env.user.has_group("agx_sarabun.group_sarabun_manager"):
            raise UserError(_("Only a Sarabun Manager may regenerate the signed PDF."))
        if self.state != "completed" or not self.is_frozen:
            raise UserError(
                _(
                    "Only a completed document has a signed PDF (ฉบับลงนาม) to regenerate."
                )
            )
        # sudo: the freeze is a system act on a read-only record (as at completion).
        doc = self.sudo()
        Attachment = self.env["ir.attachment"].sudo()
        attached = [("res_model", "=", doc._name), ("res_id", "=", doc.id)]
        frozen = Attachment.search(attached + [("res_field", "=", "signed_pdf")])
        # The visible copy _freeze_signed_copy drops into the Attachments carries the
        # very same bytes — match it by checksum, not by (user-reusable) file name.
        old_copies = Attachment.search(
            attached
            + [("res_field", "=", False), ("checksum", "in", frozen.mapped("checksum"))]
        )
        # Keep the real freeze time: regenerating is a re-render, not a re-sign.
        signed_at = doc.signed_at
        doc.write(
            {"signed_pdf": False, "signed_pdf_filename": False, "signed_at": False}
        )
        old_copies.unlink()
        doc._freeze_signed_copy()
        doc.signed_at = signed_at
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("สร้างไฟล์ PDF ฉบับลงนามใหม่แล้ว"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
