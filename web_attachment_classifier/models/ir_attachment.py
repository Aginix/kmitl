from odoo import _, fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    document_type_id = fields.Many2one(
        comodel_name="ir.attachment.document.type",
        string="Document Type",
        ondelete="restrict",
    )

    def write(self, vals):
        # Snapshot the old doctype only when it's about to change, so we
        # can post a tracking message onto the parent record's chatter
        # after the write commits.
        if "document_type_id" not in vals:
            return super().write(vals)
        before = {
            att.id: (att.res_model, att.res_id, att.name, att.document_type_id)
            for att in self
        }
        result = super().write(vals)
        for att in self:
            _res_model, _res_id, old_name, old_doctype = before[att.id]
            new_doctype = att.document_type_id
            if old_doctype == new_doctype:
                continue
            if not (att.res_model and att.res_id):
                continue
            parent_model = self.env.get(att.res_model)
            if parent_model is None or "message_post" not in dir(parent_model):
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
