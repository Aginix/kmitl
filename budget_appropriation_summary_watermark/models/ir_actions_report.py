from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from odoo import models
from odoo.modules.module import get_module_resource

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
        """Return the bytes of a single A4 page with ``text`` drawn diagonally."""
        page_size = A4
        if paperformat and paperformat.orientation == "Landscape":
            page_size = landscape(A4)
        width, height = page_size

        font_name = self._get_watermark_font_name()
        diagonal = (width**2 + height**2) ** 0.5
        font_size = 90
        while (
            font_size > 10
            and pdfmetrics.stringWidth(text, font_name, font_size) > diagonal * 0.8
        ):
            font_size -= 2

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=page_size)
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
