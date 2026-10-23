from odoo import _, fields, models

from odoo.addons.agx_change_request.models.change_request_mixin import OUTSTANDING


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    outstanding_request_count = fields.Integer(
        compute="_compute_outstanding_request_count"
    )

    def _request_files(self):
        """This file and its other revisions, when revisions are installed."""
        self.ensure_one()
        if hasattr(self, "_revision_chain"):
            return self._revision_chain()
        return self.sudo()

    def _compute_outstanding_request_count(self):
        files = {
            attachment.id: attachment._request_files().ids
            for attachment in self
            if isinstance(attachment.id, int)
        }
        # One query for all of them, however many files are shown.
        groups = (
            self.env["change.request"]
            .sudo()
            ._read_group(
                [
                    ("attachment_id", "in", [i for ids in files.values() for i in ids]),
                    ("state", "in", OUTSTANDING),
                ],
                ["attachment_id"],
                ["attachment_id"],
            )
        )
        counts = {
            group["attachment_id"][0]: group["attachment_id_count"] for group in groups
        }
        for attachment in self:
            attachment.outstanding_request_count = sum(
                counts.get(file_id, 0) for file_id in files.get(attachment.id, [])
            )

    def _attachment_format(self, legacy=False):
        # The chatter shows the same outstanding requests badge as the
        # many2many_binary widget; always sent, so a badge clears at zero.
        res_list = super()._attachment_format(legacy=legacy)
        counts = {a.id: a.outstanding_request_count for a in self}
        for res in res_list:
            res["openRequestCount"] = counts.get(res["id"], 0)
        return res_list

    def unlink(self):
        """A pinned request is cancelled, not closed, once its file is deleted."""
        if not self.env.context.get("change_request_record_unlink"):
            requests = (
                self.env["change.request"]
                .sudo()
                .search([("attachment_id", "in", self.ids)])
            )
            for request in requests:
                request._cancel(
                    _("The file %s it was pinned on was deleted.", request.file_name)
                )
        return super().unlink()
