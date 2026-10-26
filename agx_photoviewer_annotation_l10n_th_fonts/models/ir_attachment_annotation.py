from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from odoo import api, models
from odoo.modules.module import get_module_resource

FONT = "THSarabunNew"


class IrAttachmentAnnotation(models.Model):
    _inherit = "ir.attachment.annotation"

    @api.model
    def _export_font(self):
        if FONT not in pdfmetrics.getRegisteredFontNames():
            path = get_module_resource(
                "l10n_th_fonts", "static", "fonts", "THSarabunNew.ttf"
            )
            pdfmetrics.registerFont(TTFont(FONT, path))
        return FONT
