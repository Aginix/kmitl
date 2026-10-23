from markupsafe import Markup

from odoo import _, models

LATEST_ONLY = ("revision_superseded", "=", False)


class Base(models.AbstractModel):
    _inherit = "base"

    def _setup_fields(self):
        """A record shows only the latest revision among its files: the
        One2many of its attachments (by ``res_id``) leaves superseded ones
        out, as its many2many fields are rewritten on each revision."""
        super()._setup_fields()
        for field in self._fields.values():
            if (
                field.type == "one2many"
                and field.comodel_name == "ir.attachment"
                and field.inverse_name == "res_id"
                and not callable(field.domain)
                and LATEST_ONLY not in (field.domain or [])
            ):
                field.domain = list(field.domain or []) + [LATEST_ONLY]

    def _annotation_replace_revision(self, previous, revision):
        """Show ``revision`` on this record where ``previous`` was, and note
        its upload in the chatter with the new file."""
        self.ensure_one()
        record = self.sudo()
        for name, field in record._fields.items():
            if (
                field.type == "many2many"
                and field.comodel_name == "ir.attachment"
                and field.store
                and previous in record[name]
            ):
                record[name] = [(3, previous.id), (4, revision.id)]
        if "message_main_attachment_id" in record._fields:
            if record.message_main_attachment_id == previous:
                record.message_main_attachment_id = revision
        if hasattr(record, "message_post"):
            record.message_post(
                body=Markup("<p>%s</p>")
                % _(
                    "Revision %(number)s of %(file)s uploaded.",
                    number=revision.revision_number,
                    file=revision.name or "",
                ),
                subtype_xmlid="mail.mt_note",
                author_id=self.env.user.partner_id.id,
                attachment_ids=revision.ids,
            )
