# -*- coding: utf-8 -*-
import base64
import io
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.pdf import merge_pdf

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def action_print_all_reports(self):
        self.ensure_one()

        pdf_streams = []

        # Report 1 (แนวตั้ง)
        pdf1, _ = self.env.ref(
            "purchase_request.action_report_purchase_requests"
        )._render_qweb_pdf([self.request_id.id])
        pdf_streams.append(io.BytesIO(pdf1))

        # Report 2 (แนวนอน)
        pdf2, _ = self.env.ref(
            "purchase.action_report_purchase_order"
        )._render_qweb_pdf([self.id])
        pdf_streams.append(io.BytesIO(pdf2))

        # รวม PDF
        merged_pdf = merge_pdf(pdf_streams)

        return {
            "type": "ir.actions.act_url",
            "url": (
                "data:application/pdf;base64,"
                + base64.b64encode(merged_pdf).decode()
            ),
            "target": "self",
        }
