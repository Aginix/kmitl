from odoo import _, fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    document_type_id = fields.Many2one(
        comodel_name="ir.attachment.document.type",
        string="Document Type",
        ondelete="restrict",
    )

    def _attachment_format(self, legacy=False):
        # Inject document_type_id's display name into the payload mail's
        # chatter sends to the browser, so the AttachmentCard template
        # can render the same badge that the many2many_binary widget
        # shows on the form. Only attachments that actually have a
        # doctype gain the extra key.
        res_list = super()._attachment_format(legacy=legacy)
        doctype_by_id = {
            att.id: att.document_type_id.name for att in self if att.document_type_id
        }
        for res in res_list:
            if res["id"] in doctype_by_id:
                res["documentTypeName"] = doctype_by_id[res["id"]]
        return res_list

    def write(self, vals):
        # Snapshot the old doctype only when it's about to change, so we
        # can post a tracking message onto the parent record's chatter
        # after the write commits.
        if "document_type_id" not in vals:
            return super().write(vals)
        before = {att.id: (att.name, att.document_type_id) for att in self}
        result = super().write(vals)
        for att in self:
            old_name, old_doctype = before[att.id]
            new_doctype = att.document_type_id
            if old_doctype == new_doctype:
                continue
            if not (att.res_model and att.res_id):
                continue
            parent_model = self.env.get(att.res_model)
            if parent_model is None or not hasattr(parent_model, "message_post"):
                # Parent doesn't inherit mail.thread (e.g. res.users,
                # product.template attachments) — nowhere to post.
                continue
            parent = parent_model.sudo().browse(att.res_id).exists()
            if not parent:
                continue
            old_label = old_doctype.name if old_doctype else _("(none)")
            new_label = new_doctype.name if new_doctype else _("(none)")
            parent.message_post(
                body=_(
                    "Document Type of attachment <b>%(name)s</b>: "
                    "<i>%(old)s</i> → <i>%(new)s</i>",
                    name=att.name or old_name or "",
                    old=old_label,
                    new=new_label,
                )
            )
        return result
