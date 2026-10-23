from markupsafe import Markup

from odoo import _, models


class Base(models.AbstractModel):
    _inherit = "base"

    def _annotation_open_change_requests(self):
        """Change requests not closed yet on the files of these records, on
        every revision of them.

        Open ones never hold up a record by themselves: its module may call
        this to refuse a step (e.g. approving) while some are open.
        """
        Attachment = self.env["ir.attachment"].sudo()
        attachments = Attachment.search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        )
        for name, field in self._fields.items():
            if (
                field.type == "many2many"
                and field.comodel_name == "ir.attachment"
                and field.store
            ):
                attachments |= self.sudo().mapped(name)
        for attachment in attachments:
            attachments |= attachment._revision_chain()
        return (
            self.env["ir.attachment.annotation"]
            .sudo()
            .search(
                [
                    ("attachment_id", "in", attachments.ids),
                    ("change_request", "=", True),
                    ("request_state", "!=", "closed"),
                ]
            )
        )

    def _annotation_replace_revision(self, previous, revision):
        """Show ``revision`` on this record where ``previous`` was."""
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
            )
