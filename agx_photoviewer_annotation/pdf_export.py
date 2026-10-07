"""Build the Annotated export: the original file with its annotation layer
drawn on top, followed by a summary page listing the comments (ADR-0001).

Annotation geometry is stored as fractions of the page *as displayed* (top-left
origin, after the PDF ``/Rotate``), exactly as pdf.js shows it in the viewer;
the overlay is drawn in that display space and mapped back to the page's own
coordinates. Keep the shapes below in sync with ``annotation_renderer.js``.
"""

import io
import logging
from collections import defaultdict

from PIL import Image, ImageOps
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from odoo.modules.module import get_module_resource
from odoo.tools.pdf import PdfFileReader, PdfFileWriter

_logger = logging.getLogger(__name__)

# Stamps in a unit box centred on the click point (y down), scaled by half
# the stamp size.
CHECK_POINTS = [(-0.8, 0.0), (-0.25, 0.6), (0.85, -0.65)]
CROSS_LINES = [[(-0.7, -0.7), (0.7, 0.7)], [(-0.7, 0.7), (0.7, -0.7)]]
STAMP_STROKE = 0.14  # of the stamp size
RECT_WIDTH = 0.003  # of the page width
PIN_RADIUS = 0.014  # of the page width
HIGHLIGHT_OPACITY = 0.35
DEFAULT_COLOR = "#e53935"
# Longest side of the page an image is exported on (A4 height).
IMAGE_PAGE_SIZE = A4[1]

_FONT = "THSarabunNew"
_FALLBACK_FONT = "Helvetica"
_font_name = None


def _font():
    """Register the Thai font once; fall back to Helvetica on any failure."""
    global _font_name
    if _font_name is None:
        try:
            path = get_module_resource(
                "l10n_th_fonts", "static", "fonts", "THSarabunNew.ttf"
            )
            pdfmetrics.registerFont(TTFont(_FONT, path))
            _font_name = _FONT
        except Exception:  # pragma: no cover - best effort
            _logger.warning("Could not register THSarabunNew", exc_info=True)
            _font_name = _FALLBACK_FONT
    return _font_name


def _color(value):
    try:
        return HexColor(value or DEFAULT_COLOR)
    except ValueError:
        return HexColor(DEFAULT_COLOR)


def _draw_annotations(can, annotations, width, height, numbers):
    """Draw ``annotations`` on a page of ``width`` x ``height`` points whose
    origin is the bottom-left corner of the page as displayed."""

    def point(x, y):
        return x * width, height - y * height

    can.setLineCap(1)
    can.setLineJoin(1)
    for annotation in annotations:
        kind = annotation["kind"]
        geometry = annotation["geometry"]
        color = _color(annotation["color"])
        can.saveState()
        can.setStrokeColor(color)
        can.setFillColor(color)
        if kind == "pen" and len(geometry.get("points") or []) > 1:
            path = can.beginPath()
            path.moveTo(*point(*geometry["points"][0]))
            for x, y in geometry["points"][1:]:
                path.lineTo(*point(x, y))
            can.setLineWidth((geometry.get("width") or RECT_WIDTH) * width)
            can.drawPath(path, stroke=1, fill=0)
        elif kind in ("highlight", "rect"):
            left, top = point(geometry["x"], geometry["y"])
            box_width = geometry["w"] * width
            box_height = geometry["h"] * height
            if kind == "highlight":
                can.setFillAlpha(HIGHLIGHT_OPACITY)
                can.rect(
                    left, top - box_height, box_width, box_height, stroke=0, fill=1
                )
            else:
                can.setLineWidth(RECT_WIDTH * width)
                can.rect(
                    left, top - box_height, box_width, box_height, stroke=1, fill=0
                )
        elif kind in ("check", "cross"):
            centre_x, centre_y = point(geometry["x"], geometry["y"])
            size = (geometry.get("size") or 0.04) * width
            radius = size / 2

            def stamp(x, y):
                return centre_x + x * radius, centre_y - y * radius

            lines = [CHECK_POINTS] if kind == "check" else CROSS_LINES
            can.setLineWidth(size * STAMP_STROKE)
            for line in lines:
                path = can.beginPath()
                path.moveTo(*stamp(*line[0]))
                for x, y in line[1:]:
                    path.lineTo(*stamp(x, y))
                can.drawPath(path, stroke=1, fill=0)
        elif kind == "comment":
            centre_x, centre_y = point(geometry["x"], geometry["y"])
            radius = PIN_RADIUS * width
            can.circle(centre_x, centre_y, radius, stroke=0, fill=1)
            can.setFillColor(white)
            font_size = radius * 1.2
            can.setFont("Helvetica-Bold", font_size)
            can.drawCentredString(
                centre_x,
                centre_y - font_size * 0.35,
                str(numbers.get(annotation["id"], "")),
            )
        can.restoreState()


def _to_display_space(can, page_width, page_height, rotation):
    """Map the display space of a page shown with ``/Rotate rotation`` (origin
    bottom-left, y up) onto its unrotated user space; return the display size."""
    if rotation == 90:
        can.transform(0, 1, -1, 0, page_width, 0)
        return page_height, page_width
    if rotation == 180:
        can.transform(-1, 0, 0, -1, page_width, page_height)
        return page_width, page_height
    if rotation == 270:
        can.transform(0, -1, 1, 0, 0, page_height)
        return page_height, page_width
    return page_width, page_height


def _wrap(text, font, size, width):
    """Greedy wrap that also breaks Thai text, which has no spaces between words."""
    lines = []
    for paragraph in (text or "").splitlines() or [""]:
        line = ""
        for char in paragraph:
            candidate = line + char
            if not line or stringWidth(candidate, font, size) <= width:
                line = candidate
                continue
            cut = line.rfind(" ")
            if cut > 0:
                lines.append(line[:cut])
                line = line[cut + 1 :] + char
            else:
                lines.append(line)
                line = char
        lines.append(line)
    return lines


def _draw_summary(can, comments, numbers, title, page_label):
    font = _font()
    page_width, page_height = A4
    margin = 50
    line_height = 18
    text_width = page_width - 2 * margin - 20
    can.setPageSize(A4)
    y = page_height - margin

    def new_page():
        can.showPage()
        can.setPageSize(A4)
        return page_height - margin

    can.setFont(font, 22)
    for line in _wrap(title, font, 22, page_width - 2 * margin):
        can.drawString(margin, y, line)
        y -= 26
    y -= 8
    for comment in sorted(comments, key=lambda c: numbers[c["id"]]):
        header = "%s. %s %s — %s — %s" % (
            numbers[comment["id"]],
            page_label,
            comment["page"],
            comment["author"],
            comment["date"],
        )
        body = _wrap(comment["text"], font, 16, text_width)
        if y - line_height * (len(body) + 1) < margin:
            y = new_page()
        can.setFont(font, 16)
        can.setFillColor(HexColor("#555555"))
        can.drawString(margin, y, header)
        y -= line_height
        can.setFillColor(HexColor("#000000"))
        for line in body:
            if y < margin:
                y = new_page()
                can.setFont(font, 16)
            can.drawString(margin + 20, y, line)
            y -= line_height
        y -= 6
    can.showPage()


def build_annotated_pdf(content, is_pdf, annotations, comments, title, page_label):
    """Return the Annotated export as PDF bytes.

    :param bytes content: the original file (a PDF, or an image otherwise).
    :param list annotations: dicts with ``id, page, kind, geometry, color``.
    :param list comments: dicts with ``id, page, author, date, text``; listed
        on a summary page and numbered in (page, id) order like the viewer.
    """
    numbers = {
        comment["id"]: number
        for number, comment in enumerate(
            sorted(comments, key=lambda c: (c["page"], c["id"])), 1
        )
    }
    by_page = defaultdict(list)
    for annotation in annotations:
        by_page[annotation["page"]].append(annotation)

    packet = io.BytesIO()
    can = canvas.Canvas(packet)
    writer = PdfFileWriter()
    if is_pdf:
        reader = PdfFileReader(io.BytesIO(content), strict=False)
        overlay_index = {}
        for index in range(reader.getNumPages()):
            if not by_page.get(index + 1):
                continue
            page = reader.getPage(index)
            # pdf.js displays the crop box.
            box = page.cropBox
            left, bottom = float(box.getLowerLeft_x()), float(box.getLowerLeft_y())
            page_width, page_height = float(box.getWidth()), float(box.getHeight())
            rotation = int(page.get("/Rotate") or 0) % 360
            can.setPageSize((left + page_width, bottom + page_height))
            can.saveState()
            can.translate(left, bottom)
            width, height = _to_display_space(can, page_width, page_height, rotation)
            _draw_annotations(can, by_page[index + 1], width, height, numbers)
            can.restoreState()
            can.showPage()
            overlay_index[index] = len(overlay_index)
        if comments:
            _draw_summary(can, comments, numbers, title, page_label)
        can.save()
        overlay = PdfFileReader(io.BytesIO(packet.getvalue()), strict=False)
        for index in range(reader.getNumPages()):
            page = reader.getPage(index)
            if index in overlay_index:
                page.mergePage(overlay.getPage(overlay_index[index]))
            writer.addPage(page)
        for index in range(len(overlay_index), overlay.getNumPages()):
            writer.addPage(overlay.getPage(index))
    else:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(content)))
        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGBA")
        scale = IMAGE_PAGE_SIZE / max(image.size)
        width, height = image.size[0] * scale, image.size[1] * scale
        can.setPageSize((width, height))
        can.drawImage(ImageReader(image), 0, 0, width, height, mask="auto")
        _draw_annotations(can, by_page.get(1, []), width, height, numbers)
        can.showPage()
        if comments:
            _draw_summary(can, comments, numbers, title, page_label)
        can.save()
        overlay = PdfFileReader(io.BytesIO(packet.getvalue()), strict=False)
        for index in range(overlay.getNumPages()):
            writer.addPage(overlay.getPage(index))
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
