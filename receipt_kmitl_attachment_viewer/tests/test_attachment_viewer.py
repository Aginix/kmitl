# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io

from odoo.addons.receipt_kmitl.tests.common import ReceiptKmitlCommon
from odoo.tests.common import tagged
from odoo.tools.pdf import PdfFileReader

# 1x1 transparent PNG, used to exercise the image-to-PDF attachment path.
TEST_PNG_B64 = (
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    b"+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@tagged("post_install", "-at_install")
class TestAttachmentViewer(ReceiptKmitlCommon):
    def test_build_attachments_pdf_no_attachments(self):
        r1 = self._make_receipt()
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id])],
            }
        )
        pdf_content = remittance._build_attachments_pdf()
        self.assertTrue(pdf_content)

    def test_build_attachments_pdf_with_attachments(self):
        r1 = self._make_receipt()
        r2 = self._make_receipt()
        image_attachment = self.env["ir.attachment"].create(
            {
                "name": "slip.png",
                "datas": TEST_PNG_B64,
                "mimetype": "image/png",
            }
        )
        skipped_attachment = self.env["ir.attachment"].create(
            {
                "name": "notes.docx",
                "datas": base64.b64encode(b"not really a docx"),
                "mimetype": (
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
            }
        )
        r1.attachment_ids = [(6, 0, [image_attachment.id, skipped_attachment.id])]
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id, r2.id])],
            }
        )
        pdf_content = remittance._build_attachments_pdf()
        self.assertTrue(pdf_content)
        reader = PdfFileReader(io.BytesIO(pdf_content), strict=False)
        # separator(r1) + image page + separator(r2) = 3
        self.assertEqual(reader.getNumPages(), 3)

    def test_build_attachments_pdf_page_alignment(self):
        """Separator pages: one per receipt, plus one page per attachment
        page — r1 has one image (1 page), r2 has none."""
        r1 = self._make_receipt()
        r2 = self._make_receipt()
        image_attachment = self.env["ir.attachment"].create(
            {
                "name": "slip.png",
                "datas": TEST_PNG_B64,
                "mimetype": "image/png",
            }
        )
        r1.attachment_ids = [(6, 0, [image_attachment.id])]
        remittance = self.env["kmitl.receipt.remittance"].create(
            {
                "department_analytic_id": self.dept_a.id,
                "receipt_ids": [(6, 0, [r1.id, r2.id])],
            }
        )
        pdf_content = remittance._build_attachments_pdf()
        reader = PdfFileReader(io.BytesIO(pdf_content), strict=False)
        self.assertEqual(reader.getNumPages(), 3)

    def test_separator_renders_skipped_attachment_names(self):
        r1 = self._make_receipt()
        html = self.env["ir.actions.report"]._render_qweb_html(
            "receipt_kmitl_attachment_viewer.action_report_receipt_kmitl_attachments_separator",
            r1.ids,
            data={"skipped_map": {str(r1.id): ["notes.docx"]}},
        )[0]
        if isinstance(html, bytes):
            html = html.decode("utf-8")
        self.assertIn("notes.docx", html)
