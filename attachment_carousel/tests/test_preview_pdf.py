# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import os
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"
_DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _fake_convert_ok(cmd, **kwargs):
    """Stub for subprocess.run that pretends soffice succeeded and dropped a
    minimal PDF next to the source file."""
    # cmd = [binary, "--headless", "--convert-to", "pdf", "--outdir", tmpdir, src_path]
    src_path = cmd[-1]
    outdir = cmd[-2]
    pdf_path = os.path.join(outdir, os.path.splitext(os.path.basename(src_path))[0] + ".pdf")
    with open(pdf_path, "wb") as fh:
        fh.write(_MINIMAL_PDF)

    class _Completed:
        stdout = b""
        stderr = b""

    return _Completed()


@tagged("post_install", "-at_install")
class TestAttachmentPreviewPdf(TransactionCase):
    def _make_attachment(self, name, mimetype, content=b"payload"):
        return self.env["ir.attachment"].create(
            {
                "name": name,
                "datas": base64.b64encode(content),
                "mimetype": mimetype,
            }
        )

    def test_pdf_returns_raw_bytes(self):
        pdf = self._make_attachment("doc.pdf", "application/pdf", _MINIMAL_PDF)
        self.assertEqual(pdf.get_preview_pdf(), _MINIMAL_PDF)

    def test_unsupported_mimetype_returns_none(self):
        img = self._make_attachment("logo.png", "image/png", b"\x89PNG\r\n")
        self.assertIsNone(img.get_preview_pdf())

    def test_office_converts_and_caches(self):
        docx = self._make_attachment("brief.docx", _DOCX_MIME, b"fake docx bytes")
        target = (
            "odoo.addons.attachment_carousel.models.ir_attachment."
            "subprocess.run"
        )
        with patch(target, side_effect=_fake_convert_ok) as run:
            pdf = docx.get_preview_pdf()
            self.assertEqual(pdf, _MINIMAL_PDF)
            self.assertEqual(run.call_count, 1)
            # Cache is now populated; a second call must not shell out again.
            docx.invalidate_recordset()
            pdf2 = docx.get_preview_pdf()
            self.assertEqual(pdf2, _MINIMAL_PDF)
            self.assertEqual(run.call_count, 1)

    def test_cache_invalidates_on_source_change(self):
        docx = self._make_attachment("brief.docx", _DOCX_MIME, b"v1")
        target = (
            "odoo.addons.attachment_carousel.models.ir_attachment."
            "subprocess.run"
        )
        with patch(target, side_effect=_fake_convert_ok) as run:
            docx.get_preview_pdf()
            self.assertEqual(run.call_count, 1)
            # Re-upload changes checksum → cache is stale → convert again.
            docx.write({"datas": base64.b64encode(b"v2-different")})
            docx.get_preview_pdf()
            self.assertEqual(run.call_count, 2)

    def test_missing_binary_raises_user_error(self):
        docx = self._make_attachment("brief.docx", _DOCX_MIME, b"payload")
        target = (
            "odoo.addons.attachment_carousel.models.ir_attachment."
            "subprocess.run"
        )
        with patch(target, side_effect=FileNotFoundError("no soffice")):
            with self.assertRaises(UserError):
                docx.get_preview_pdf()
