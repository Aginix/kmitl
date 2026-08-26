# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import _, fields, models


class KmitlReceiptPreview(models.TransientModel):
    _name = "kmitl.receipt.preview"
    _description = "Receipt Preview"

    receipt_id = fields.Many2one("kmitl.receipt", required=True, readonly=True)
    preview_html = fields.Html(readonly=True, sanitize=False)

    def action_confirm_print(self):
        self.ensure_one()
        receipt = self.receipt_id
        report = self.env["ir.actions.report"]
        pdf, _fmt = report._render_qweb_pdf(
            "receipt_kmitl.action_report_receipt_kmitl", receipt.ids
        )
        fname = "%s.pdf" % (receipt.name or "receipt").replace("/", "-")
        attachment = self.env["ir.attachment"].create(
            {
                "name": fname,
                "type": "binary",
                "datas": base64.b64encode(pdf),
                "mimetype": "application/pdf",
                "res_model": "kmitl.receipt",
                "res_id": receipt.id,
            }
        )
        receipt.write(
            {
                "is_printed": True,
                "message_main_attachment_id": attachment.id,
            }
        )
        receipt.message_post(
            body=_("Receipt printed."),
            attachment_ids=[attachment.id],
        )
        return {"type": "ir.actions.act_window_close"}
