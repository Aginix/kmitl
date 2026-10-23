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
        Request = self.env["change.request"].sudo()
        for attachment in self:
            if not isinstance(attachment.id, int):
                attachment.outstanding_request_count = 0
                continue
            attachment.outstanding_request_count = Request.search_count(
                [
                    ("attachment_id", "in", attachment._request_files().ids),
                    ("state", "in", OUTSTANDING),
                ]
            )

    def _attachment_format(self, legacy=False):
        # The chatter shows the same outstanding requests badge as the
        # many2many_binary widget.
        res_list = super()._attachment_format(legacy=legacy)
        counts = {a.id: a.outstanding_request_count for a in self}
        for res in res_list:
            if counts.get(res["id"]):
                res["openRequestCount"] = counts[res["id"]]
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
