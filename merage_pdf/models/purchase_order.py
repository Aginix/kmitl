# -*- coding: utf-8 -*-
import base64
import io
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.pdf import merge_pdf

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_print_all_reports(self):
        self.ensure_one()

        pdf_streams = []

        # Report 1 (แนวตั้ง)
        pdf1, _ = self.env['ir.actions.report']._render_qweb_pdf("purchase_request.action_report_purchase_requests", self.request_id.id)
        pdf_streams.append(pdf1)

        # Report 2 (แนวนอน)
        pdf2, _ = self.env['ir.actions.report']._render_qweb_pdf("purchase.action_report_purchase_order", self.id)
        pdf_streams.append(pdf2)

        # รวม PDF
        merged_pdf = merge_pdf(pdf_streams)

        attachment = self.env["ir.attachment"].create({
            "name": "merged_report.pdf",
            "type": "binary",
            "datas": base64.b64encode(merged_pdf),
            "mimetype": "application/pdf",
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
