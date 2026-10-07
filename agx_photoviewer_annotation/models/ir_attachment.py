from odoo import fields, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    annotation_count = fields.Integer(compute="_compute_annotation_count")

    def _compute_annotation_count(self):
        counts = self.env["ir.attachment.annotation"]._count_by_attachment(self.ids)
        for attachment in self:
            attachment.annotation_count = counts.get(attachment.id, 0)

    def _attachment_format(self, legacy=False):
        # Ship the count to the chatter so it can show the same badge as the
        # many2many_binary widget; only annotated attachments gain the key.
        res_list = super()._attachment_format(legacy=legacy)
        counts = self.env["ir.attachment.annotation"]._count_by_attachment(self.ids)
        for res in res_list:
            if counts.get(res["id"]):
                res["annotationCount"] = counts[res["id"]]
        return res_list
