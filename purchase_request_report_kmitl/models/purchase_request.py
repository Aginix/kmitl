# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ["purchase.request", "thai.date.mixin"]

    def button_to_approve(self):
        """Override to generate and attach report PDF after submission"""
        res = super().button_to_approve()

        for record in self:
            # Generate the purchase request report PDF
            report = self.env.ref("purchase_request.action_report_purchase_requests")
            if report:
                pdf_content, _ = report._render_qweb_pdf(record.ids)

                # Create attachment
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": f"Purchase Request - {record.name}.pdf",
                        "type": "binary",
                        "datas": pdf_content,
                        "res_model": record._name,
                        "res_id": record.id,
                        "mimetype": "application/pdf",
                    }
                )

                # Set as main attachment
                record.message_main_attachment_id = attachment

                # Post to chatter to make it always visible
                record.message_post(
                    body="Purchase Request Report has been generated.",
                    attachment_ids=[Command.link(attachment.id)],
                )

                _logger.info(
                    "Generated and attached purchase request report for %s", record.name
                )

        return res
