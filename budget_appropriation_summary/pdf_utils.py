"""Helpers for post-processing merged report PDFs.

The budget book is assembled by rendering each sub-report on its own
paper format and merging the results (see ``merge_pdf``).  Because the
individual reports know nothing about their final position in the book,
running page numbers are stamped here, once, on the merged PDF.
"""
import io
import logging

from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from odoo.modules.module import get_module_resource
from odoo.tools.pdf import PdfFileReader, PdfFileWriter

_logger = logging.getLogger(__name__)

# THSarabunNew ships with l10n_th_fonts (a dependency of this module) so the
# page label can contain Thai code pages (e.g. "ก-1") without tofu boxes.
_PAGE_FONT = "THSarabunNew"
_FALLBACK_FONT = "Helvetica"
_font_name = None


def _page_font():
    """Register the Thai font once; fall back to Helvetica on any failure."""
    global _font_name
    if _font_name is not None:
        return _font_name
    try:
        path = get_module_resource(
            "l10n_th_fonts", "static", "fonts", "THSarabunNew.ttf"
        )
        if path:
            pdfmetrics.registerFont(TTFont(_PAGE_FONT, path))
            _font_name = _PAGE_FONT
        else:
            _font_name = _FALLBACK_FONT
    except Exception:  # pragma: no cover - font registration is best effort
        _logger.warning(
            "Could not register THSarabunNew for page numbers; "
            "falling back to Helvetica",
            exc_info=True,
        )
        _font_name = _FALLBACK_FONT
    return _font_name


def stamp_page_numbers(pdf_bytes, label_for_page, font_size=14):
    """Overlay a page label at the bottom-centre of every page.

    :param bytes pdf_bytes: source PDF.
    :param label_for_page: ``callable(page_index)`` returning the label string
        for a 0-based page index; return a falsy value to skip a page.
    :param int font_size: label font size in points.
    :return bytes: the stamped PDF (or the original bytes on any failure).
    """
    if not pdf_bytes:
        return pdf_bytes
    try:
        reader = PdfFileReader(io.BytesIO(pdf_bytes), strict=False)
        num_pages = reader.getNumPages()
        font = _page_font()

        packet = io.BytesIO()
        can = canvas.Canvas(packet)
        for index in range(num_pages):
            page = reader.getPage(index)
            width = float(abs(page.mediaBox.getWidth()))
            height = float(abs(page.mediaBox.getHeight()))
            can.setPageSize((width, height))
            label = label_for_page(index)
            if label:
                can.setFont(font, font_size)
                # 5 mm from the bottom edge keeps the label inside every
                # report's bottom margin (the smallest is 8 mm).
                can.drawCentredString(width / 2.0, 5 * mm, label)
            can.showPage()
        can.save()
        packet.seek(0)

        overlay = PdfFileReader(packet, strict=False)
        writer = PdfFileWriter()
        for index in range(num_pages):
            page = reader.getPage(index)
            if "/Annots" in page:
                del page["/Annots"]
            page.mergePage(overlay.getPage(index))
            writer.addPage(page)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    except Exception:  # pragma: no cover - never break printing over numbering
        _logger.warning("Could not stamp page numbers on PDF", exc_info=True)
        return pdf_bytes
