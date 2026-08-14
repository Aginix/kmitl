import logging
from base64 import b64decode
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from odoo import models
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)

WATERMARK_FONT = "BudgetWatermarkTHSarabun"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _get_watermark(self, report_ref):
        """Add a text watermark generated on the fly for the budget summary print.

        The base OCA module only supports PDF/image watermarks. We keep that
        behaviour and only step in when ``budget_watermark_text`` is present in
        the context (set by ``action_print_report_watermark``), rendering the
        text to a one-page PDF sized to the report's own paperformat so it lines
        up on both portrait and landscape sub-reports.
        """
        watermark = super()._get_watermark(report_ref)
        if watermark:
            return watermark
        text = self.env.context.get("budget_watermark_text")
        if not text:
            return watermark
        report_sudo = self._get_report(report_ref)
        return self._render_text_watermark(text, report_sudo.paperformat_id)

    def _render_text_watermark(self, text, paperformat):
        """Return a single-page PDF with the company logo and ``text`` watermark.

        Draws the company logo faded in the centre (letterhead style) with the
        watermark text on top, diagonally. Sized to the report's paperformat so
        it lines up on both portrait and landscape sub-reports.
        """
        page_size = A4
        if paperformat and paperformat.orientation == "Landscape":
            page_size = landscape(A4)
        width, height = page_size

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=page_size)
        self._draw_watermark_logo(pdf, width, height)

        font_name = self._get_watermark_font_name()
        diagonal = (width**2 + height**2) ** 0.5
        font_size = 90
        while (
            font_size > 10
            and pdfmetrics.stringWidth(text, font_name, font_size) > diagonal * 0.8
        ):
            font_size -= 2

        pdf.saveState()
        pdf.setFont(font_name, font_size)
        pdf.setFillColor(colors.Color(0.5, 0.5, 0.5, alpha=0.18))
        pdf.translate(width / 2, height / 2)
        pdf.rotate(45)
        pdf.drawCentredString(0, 0, text)
        pdf.restoreState()
        pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    def _draw_watermark_logo(self, pdf, width, height):
        """Draw the company logo faded and centred as a background, if available."""
        logo = self.env.company.logo
        if not logo:
            return
        try:
            image = ImageReader(BytesIO(b64decode(logo)))
            image_width, image_height = image.getSize()
            scale = min(width * 0.45 / image_width, height * 0.45 / image_height)
            draw_width = image_width * scale
            draw_height = image_height * scale
            pdf.saveState()
            pdf.setFillAlpha(0.12)
            pdf.drawImage(
                image,
                (width - draw_width) / 2,
                (height - draw_height) / 2,
                width=draw_width,
                height=draw_height,
                mask="auto",
                preserveAspectRatio=True,
            )
            pdf.restoreState()
        except Exception:
            _logger.warning("ไม่สามารถวาดโลโก้บริษัทลงในลายน้ำได้", exc_info=True)

    def _get_watermark_font_name(self):
        """Register (once) and return a Thai-capable font, falling back to Helvetica."""
        if WATERMARK_FONT in pdfmetrics.getRegisteredFontNames():
            return WATERMARK_FONT
        font_path = get_module_resource(
            "l10n_th_fonts", "static/fonts", "THSarabunNew.ttf"
        )
        if not font_path:
            return "Helvetica"
        pdfmetrics.registerFont(TTFont(WATERMARK_FONT, font_path))
        return WATERMARK_FONT
