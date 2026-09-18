# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import io

from odoo import _, models
from odoo.tools.pdf import PdfFileReader, PdfFileWriter, to_pdf_stream

SEPARATOR_REPORT = "receipt_kmitl_attachment_viewer.action_report_receipt_kmitl_attachments_separator"

# Cap the file list printed on a receipt's separator page — otherwise a
# receipt with dozens of unsupported attachments pushes its separator past
# one page, breaking the index-based page matching in _build_attachments_pdf.
MAX_SKIPPED_LISTED = 8


class ReceiptRemittance(models.Model):
    _inherit = "kmitl.receipt.remittance"

    def action_view_attachments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/receipt_kmitl/remittance/%s/attachments" % self.id,
            "target": "new",
        }

    def _build_attachments_pdf(self):
        self.ensure_one()
        receipts = self.receipt_ids.sorted(key=lambda r: r.name or "")
        # force_report_rendering: get real PDF bytes even under the test
        # runner, which otherwise short-circuits to HTML (see
        # ir.actions.report._render_qweb_pdf).
        report = self.env["ir.actions.report"].with_context(
            force_report_rendering=True
        ).sudo()

        if not any(receipt.attachment_ids for receipt in receipts):
            pdf_content, _report_type = report._render_qweb_pdf(
                "receipt_kmitl_attachment_viewer.action_report_receipt_kmitl_no_attachments",
                [self.id],
            )
            return pdf_content

        attachment_streams = {}
        skipped_map = {}
        for receipt in receipts:
            streams = []
            skipped = []
            for attachment in receipt.attachment_ids.sudo():
                stream = to_pdf_stream(attachment)
                if stream is None:
                    skipped.append(attachment.name)
                else:
                    streams.append(stream)
            attachment_streams[receipt.id] = streams
            if skipped:
                listed = skipped[:MAX_SKIPPED_LISTED]
                if len(skipped) > MAX_SKIPPED_LISTED:
                    listed.append(
                        _("… and %s more file(s)")
                        % (len(skipped) - MAX_SKIPPED_LISTED)
                    )
                skipped_map[str(receipt.id)] = listed

        separator_pdf, _report_type = report._render_qweb_pdf(
            SEPARATOR_REPORT, receipts.ids, data={"skipped_map": skipped_map},
        )
        separator_reader = PdfFileReader(io.BytesIO(separator_pdf), strict=False)

        # Normally one separator page per receipt, matched by index. If a
        # skipped-files list pushed some receipt's separator past one page,
        # the index no longer lines up with any receipt — fall back to
        # rendering each receipt's separator individually so pages can never
        # be silently mismatched.
        one_page_each = separator_reader.getNumPages() == len(receipts)
        writer = PdfFileWriter()
        readers = [separator_reader]  # keep readers alive for lazy page reads
        for index, receipt in enumerate(receipts):
            if one_page_each:
                writer.addPage(separator_reader.getPage(index))
            else:
                one_pdf, _report_type = report._render_qweb_pdf(
                    SEPARATOR_REPORT, [receipt.id], data={"skipped_map": skipped_map},
                )
                one_reader = PdfFileReader(io.BytesIO(one_pdf), strict=False)
                readers.append(one_reader)
                for page in range(one_reader.getNumPages()):
                    writer.addPage(one_reader.getPage(page))
            for stream in attachment_streams[receipt.id]:
                stream.seek(0)
                attachment_reader = PdfFileReader(stream, strict=False)
                readers.append(attachment_reader)
                for page in range(attachment_reader.getNumPages()):
                    writer.addPage(attachment_reader.getPage(page))

        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()
