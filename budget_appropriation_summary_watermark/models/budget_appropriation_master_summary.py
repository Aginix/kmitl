import base64
from io import BytesIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.pdf import PdfFileReader, PdfFileWriter


class BudgetAppropriationMasterSummary(models.Model):
    _inherit = "budget.appropriation.master.summary"

    watermark_pdf = fields.Binary(
        string="ไฟล์ลายน้ำ (PDF)",
        attachment=True,
        help="ไฟล์ PDF ลายน้ำ (ควรมีพื้นหลังโปร่งใส) 1 หน้า "
        "ระบบจะซ้อนทับบนทุกหน้าของไฟล์ฉบับสมบูรณ์",
    )
    watermark_pdf_filename = fields.Char(string="ชื่อไฟล์ลายน้ำ")
    watermark_pages = fields.Char(
        string="หน้าที่ใส่ลายน้ำ",
        help='ระบุเลขหน้าที่จะใส่ลายน้ำ เช่น "2,3,7,60-90" '
        "(เว้นว่าง = ใส่ทุกหน้า) เลขหน้าเริ่มที่ 1",
    )
    final_document_watermarked = fields.Binary(
        string="ไฟล์ฉบับสมบูรณ์ (พร้อมลายน้ำ)",
        attachment=True,
        readonly=True,
        help="ฉบับเผยแพร่ = ไฟล์ฉบับสมบูรณ์ที่ซ้อนลายน้ำแล้ว "
        "สร้างใหม่จากไฟล์ต้นฉบับได้เสมอ",
    )
    final_document_watermarked_filename = fields.Char(
        string="ชื่อไฟล์ฉบับเผยแพร่",
    )

    @api.onchange("final_document", "watermark_pdf", "watermark_pages")
    def _onchange_clear_watermarked(self):
        """A published copy is stale once any input changes — drop it."""
        self.final_document_watermarked = False
        self.final_document_watermarked_filename = False

    def write(self, vals):
        # Re-uploading the source or the watermark, or changing the page
        # selection, invalidates the published copy — unless this very write is
        # the one publishing it.
        if (
            "final_document" in vals
            or "watermark_pdf" in vals
            or "watermark_pages" in vals
        ) and "final_document_watermarked" not in vals:
            vals = dict(
                vals,
                final_document_watermarked=False,
                final_document_watermarked_filename=False,
            )
        return super().write(vals)

    def action_generate_watermarked(self):
        self.ensure_one()
        if not self.final_document:
            raise UserError(_("กรุณาอัปโหลดไฟล์ฉบับสมบูรณ์ก่อน"))
        if not self.watermark_pdf:
            raise UserError(_("กรุณาอัปโหลดไฟล์ลายน้ำ (PDF) ก่อน"))
        watermarked = self._apply_pdf_watermark(
            base64.b64decode(self.final_document),
            base64.b64decode(self.watermark_pdf),
            self.watermark_pages,
        )
        self.write(
            {
                "final_document_watermarked": base64.b64encode(watermarked),
                "final_document_watermarked_filename": self._watermarked_filename(),
            }
        )

    def _watermarked_filename(self):
        base_name = self.final_document_filename or self._get_pdf_filename()
        if base_name.lower().endswith(".pdf"):
            base_name = base_name[:-4]
        return f"{base_name}-ลายน้ำ.pdf"

    @api.model
    def _parse_page_ranges(self, spec):
        """Parse a print-style page spec ("2,3,7,60-90") into a set of 1-based ints.

        Returns None when the spec is empty (meaning "all pages"). Raises a
        friendly error on malformed input.
        """
        if not spec or not spec.strip():
            return None
        pages = set()
        for token in spec.split(","):
            token = token.strip()
            if not token:
                continue
            start, sep, end = token.partition("-")
            start, end = start.strip(), (end.strip() if sep else start.strip())
            if not start.isdigit() or not end.isdigit():
                raise UserError(
                    _('รูปแบบหน้าไม่ถูกต้อง: "%s" (ตัวอย่างที่ถูก: 2,3,7,60-90)')
                    % token
                )
            first, last = int(start), int(end)
            if first > last:
                first, last = last, first
            pages.update(range(first, last + 1))
        return pages

    def _apply_pdf_watermark(self, document_bytes, watermark_bytes, page_spec=None):
        """Overlay the watermark's first page on top of the selected document pages.

        The watermark is scaled **uniformly** (aspect-preserving) to fit each
        target page — never stretched. Portrait pages anchor it to the
        bottom-right corner (so a corner-placed mark stays flush); landscape
        pages centre it (a portrait watermark then sits balanced in the middle
        instead of shoved to one side). Follows odoo.tools.pdf.add_banner
        (per-page overlay + stripping /Annots to avoid PyPDF2 errors).
        """
        try:
            reader = PdfFileReader(BytesIO(document_bytes), strict=False)
            document_pages = reader.getNumPages()
            watermark_pages = PdfFileReader(
                BytesIO(watermark_bytes), strict=False
            ).getNumPages()
        except Exception as exc:
            raise UserError(
                _("ไม่สามารถอ่านไฟล์ PDF ได้ กรุณาตรวจสอบว่าเป็นไฟล์ PDF ที่ถูกต้อง")
            ) from exc
        if not document_pages:
            raise UserError(_("ไฟล์ฉบับสมบูรณ์ไม่มีหน้าเนื้อหา"))
        if not watermark_pages:
            raise UserError(_("ไฟล์ลายน้ำไม่มีหน้าเนื้อหา"))

        selected = self._parse_page_ranges(page_spec)

        writer = PdfFileWriter()
        for index in range(document_pages):
            page = reader.getPage(index)
            # Pages outside the selection are copied through untouched.
            if selected is not None and (index + 1) not in selected:
                writer.addPage(page)
                continue
            if "/Annots" in page:
                del page["/Annots"]
            # Re-read a clean watermark page per target so PyPDF2 never carries
            # merged resources from one page to the next.
            watermark_page = PdfFileReader(
                BytesIO(watermark_bytes), strict=False
            ).getPage(0)
            page_width = float(abs(page.mediaBox.getWidth()))
            page_height = float(abs(page.mediaBox.getHeight()))
            wm_width = float(abs(watermark_page.mediaBox.getWidth())) or page_width
            wm_height = float(abs(watermark_page.mediaBox.getHeight())) or page_height
            # Uniform (aspect-preserving) scale to fit — never stretched.
            # Portrait: anchor bottom-right so a corner mark stays flush.
            # Landscape: centre so a portrait watermark sits balanced.
            scale = min(page_width / wm_width, page_height / wm_height)
            if page_width > page_height:
                offset_x = (page_width - wm_width * scale) / 2
                offset_y = (page_height - wm_height * scale) / 2
            else:
                offset_x = page_width - wm_width * scale
                offset_y = 0
            page.mergeTransformedPage(
                watermark_page,
                (scale, 0, 0, scale, offset_x, offset_y),
            )
            writer.addPage(page)

        output = BytesIO()
        writer.write(output)
        return output.getvalue()
