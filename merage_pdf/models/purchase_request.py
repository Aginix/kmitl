# -*- coding: utf-8 -*-
import base64
import io
import logging

from PyPDF2 import PdfMerger

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def action_print_all_reports(self):
        self.ensure_one()

        merger = PdfMerger()

        # Report 1 (แนวตั้ง)
        pdf1, _ = self.env.ref(
            'purchase_request.report_purchase_request'
        )._render_qweb_pdf(self.id)
        merger.append(io.BytesIO(pdf1))

        # Report 2 (แนวนอน / คนละโมเดล)
        pdf2, _ = self.env.ref(
            'purchase_order_report_kmitl.report_purchase_order_kmitl'
        )._render_qweb_pdf(self.id)
        merger.append(io.BytesIO(pdf2))

        # รวม PDF
        output = io.BytesIO()
        merger.write(output)
        merger.close()

        pdf_content = output.getvalue()

        return {
            "type": "ir.actions.report",
            "report_type": "qweb-pdf",
            "data": {
                "content": base64.b64encode(pdf_content),
                "name": "combined_report.pdf",
            },
        }
