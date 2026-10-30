# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models

# A faint diagonal mark on the dry run: it is not the official หนังสือ.
WATERMARK_STYLE = (
    "<style>"
    '.page::before{content:"ตัวอย่าง";position:absolute;top:40%;left:0;right:0;'
    "text-align:center;font-size:160px;font-weight:bold;"
    "transform:rotate(-30deg);color:rgba(0,0,0,.07);"
    "pointer-events:none;z-index:10;}"
    "</style>"
)


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def action_preview_sarabun_document(self):
        """The 'ดูตัวอย่างเอกสาร' button: the live หนังสือ's own preview once it
        exists, else a dry run of the one Create Document would create (mirrors
        ``disbursement_sarabun_preview``)."""
        self.ensure_one()
        if self.sarabun_has_live_document:
            return self.active_sarabun_document_id.action_open_pdf_preview()
        return {
            "type": "ir.actions.client",
            "tag": "agx_approval_sarabun_draft_preview",
            "name": _("ตัวอย่างเอกสาร (Preview)"),
            "target": "new",
            "params": {"url": f"/approval/request/{self.id}/sarabun_preview"},
        }

    def _render_sarabun_draft_preview_html(self):
        """A4-framed HTML of the หนังสือ this request would produce, watermarked.

        The หนังสือ is an unsaved ``new()`` record built from the same vals Create
        Document uses: no number, no route, nothing written. ``new()`` skips
        defaults, so they are applied first (they have no side effects)."""
        self.ensure_one()
        Doc = self.env["sarabun.document"].sudo()
        doc = Doc.new(
            {
                **Doc.default_get(list(Doc._fields)),
                **self._prepare_sarabun_document_vals(),
            }
        )
        Report = self.env["ir.actions.report"].sudo()
        # The ref may be a report action xmlid (agx_sarabun's default) or a
        # report_name (agx_sarabun_layout); _render_template needs the latter.
        report_name = Report._get_report(doc._get_no_source_report_ref()).report_name
        html = Report._render_template(
            report_name,
            {
                "docs": doc,
                "doc_ids": [],
                "doc_model": "sarabun.document",
                "report_type": "html",
            },
        ).decode("utf-8")
        if "</body>" in html:
            html = html.replace("</body>", WATERMARK_STYLE + "</body>", 1)
        else:
            html += WATERMARK_STYLE
        return doc._frame_preview_html(html)
