# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import io

from reportlab.pdfgen import canvas

from odoo import _, api, fields, models
from odoo.tools.pdf import PdfFileReader, PdfFileWriter, to_pdf_stream

SEPARATOR_REPORT = (
    "disbursement_attachment_viewer.report_disbursement_attachments_separator"
)
EMPTY_REPORT = (
    "disbursement_attachment_viewer.report_disbursement_no_attachments"
)

# Cap the file list printed on the DR's cover — a DR with dozens of
# unsupported attachments would push the cover past one page otherwise,
# breaking the "cover + files" layout.
MAX_SKIPPED_LISTED = 8


def _make_dr_stamp(width, height, text):
    """Build a single-page PDF stamp sized (width, height) containing the DR
    number at the top-right corner over a white pill, ready to be merged onto
    an attachment page via PageObject.mergePage()."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    label = "%s" % text
    font_name, font_size = "Helvetica-Bold", 10
    text_width = c.stringWidth(label, font_name, font_size)
    pad_x, pad_y = 6, 4
    right_margin, top_margin = 18, 18
    box_w = text_width + pad_x * 2
    box_h = font_size + pad_y * 2
    box_x = width - right_margin - box_w
    box_y = height - top_margin - box_h
    c.setFillColorRGB(1, 1, 1)
    c.setStrokeColorRGB(0.12, 0.18, 0.24)
    c.setLineWidth(0.6)
    c.roundRect(box_x, box_y, box_w, box_h, 3, stroke=1, fill=1)
    c.setFillColorRGB(0.12, 0.18, 0.24)
    c.setFont(font_name, font_size)
    c.drawRightString(width - right_margin - pad_x, box_y + pad_y, label)
    c.save()
    buf.seek(0)
    return PdfFileReader(buf, strict=False).getPage(0)


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    attachment_count = fields.Integer(
        compute="_compute_attachment_count",
        compute_sudo=True,
    )

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    def action_view_attachments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/disbursement/request/%s/attachments" % self.id,
            "target": "new",
        }

    def _build_attachments_pdf(self):
        self.ensure_one()
        # force_report_rendering: get real PDF bytes even under the test runner,
        # which otherwise short-circuits to HTML (see
        # ir.actions.report._render_qweb_pdf).
        report = self.env["ir.actions.report"].with_context(
            force_report_rendering=True
        ).sudo()

        if not self.attachment_ids:
            pdf_content, _report_type = report._render_qweb_pdf(
                EMPTY_REPORT, [self.id],
            )
            return pdf_content

        streams = []
        skipped = []
        for attachment in self.attachment_ids.sudo():
            stream = to_pdf_stream(attachment)
            if stream is None:
                skipped.append(attachment.name)
            else:
                streams.append(stream)

        skipped_map = {}
        if skipped:
            listed = skipped[:MAX_SKIPPED_LISTED]
            if len(skipped) > MAX_SKIPPED_LISTED:
                listed.append(
                    _("… and %s more file(s)")
                    % (len(skipped) - MAX_SKIPPED_LISTED)
                )
            skipped_map[str(self.id)] = listed

        cover_pdf, _report_type = report._render_qweb_pdf(
            SEPARATOR_REPORT, [self.id], data={"skipped_map": skipped_map},
        )
        cover_reader = PdfFileReader(io.BytesIO(cover_pdf), strict=False)

        writer = PdfFileWriter()
        readers = [cover_reader]  # keep readers alive for lazy page reads
        for page_index in range(cover_reader.getNumPages()):
            writer.addPage(cover_reader.getPage(page_index))
        for stream in streams:
            stream.seek(0)
            attachment_reader = PdfFileReader(stream, strict=False)
            readers.append(attachment_reader)
            for page_index in range(attachment_reader.getNumPages()):
                page = attachment_reader.getPage(page_index)
                # Stamp each attachment page with the DR number so a loose
                # page can always be traced back to its request. Sized to
                # the page's own mediaBox so it lands in the visible
                # top-right corner regardless of page size.
                stamp = _make_dr_stamp(
                    float(page.mediaBox.getWidth()),
                    float(page.mediaBox.getHeight()),
                    self.name or "",
                )
                page.mergePage(stamp)
                writer.addPage(page)

        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()
