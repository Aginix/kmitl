# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import io

from markupsafe import Markup

from odoo import models
from odoo.tools.pdf import PdfFileReader, PdfFileWriter

# A faint diagonal mark on the dry run: it is not the official หนังสือ.
WATERMARK_STYLE = Markup(
    "<style>"
    ".page{position:relative;}"
    '.page::after{content:"ตัวอย่าง";position:absolute;top:40%;left:0;right:0;'
    "text-align:center;font-size:160px;font-weight:bold;"
    # wkhtmltopdf's old WebKit only knows the prefixed transform.
    "-webkit-transform:rotate(-30deg);transform:rotate(-30deg);"
    "color:rgba(0,0,0,.07);"
    "pointer-events:none;z-index:10;}"
    "</style>"
)


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    def action_preview_sarabun_document(self):
        """The 'ดูตัวอย่างเอกสาร' button (ADR 0007): opens a printable PDF in a new
        tab — the live หนังสือ's own PDF once it exists, else a dry run of the one
        Submit to Sarabun would create."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/disbursement/request/{self.id}/sarabun_preview",
            "target": "new",
        }

    def _get_sarabun_preview_pdf(self):
        """(pdf, filename) behind the button. The PDF is titled with the request
        number (DR/69/0001 -> DR_69_0001): browsers show that title on the tab."""
        self.ensure_one()
        if self.sarabun_has_live_document:
            doc = self.active_sarabun_document_id
            doc.check_access_rights("read")
            doc.check_access_rule("read")
            pdf = doc._get_official_pdf()
        else:
            pdf = self._render_sarabun_draft_preview_pdf()
        title = self.display_name.replace("/", "_")
        writer = PdfFileWriter()
        writer.appendPagesFromReader(PdfFileReader(io.BytesIO(pdf), strict=False))
        writer.addMetadata({"/Title": title})
        stream = io.BytesIO()
        writer.write(stream)
        return stream.getvalue(), f"{title}.pdf"

    def _render_sarabun_draft_preview_pdf(self):
        """PDF of the หนังสือ this request would produce, watermarked.

        The หนังสือ is an unsaved ``new()`` record built from the same vals Submit
        to Sarabun uses: no number, no route, nothing written. ``new()`` skips
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
                "report_type": "pdf",
            },
        )
        # The same html -> wkhtmltopdf steps as _render_qweb_pdf, which needs
        # saved res_ids; the watermark goes into each rebuilt body's <head>.
        Report = Report.with_context(debug=False)
        bodies, _ids, header, footer, paperformat_args = Report._prepare_html(
            html, report_model="sarabun.document"
        )
        head_end = Markup("</head>")
        bodies = [
            body.replace(head_end, WATERMARK_STYLE + head_end, 1) for body in bodies
        ]
        return Report._run_wkhtmltopdf(
            bodies,
            report_ref=report_name,
            header=header,
            footer=footer,
            specific_paperformat_args=paperformat_args,
        )
