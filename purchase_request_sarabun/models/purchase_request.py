# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ["purchase.request", "sarabun.document.mixin"]

    def _prepare_sarabun_document_vals(self):
        """Prepare values for creating a sarabun document."""
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = _("Purchase Request: %s") % self.name
        vals["content"] = self._get_sarabun_content()
        return vals

    def _get_sarabun_content(self):
        """Generate HTML content for sarabun document."""
        self.ensure_one()
        lines_html = "".join(
            f"<tr><td>{line.product_id.name or line.name}</td>"
            f"<td style='text-align: right;'>{line.product_qty}</td>"
            f"<td>{line.product_uom_id.name}</td></tr>"
            for line in self.line_ids
        )
        return _(
            "<p><strong>Requested by:</strong> %(requested_by)s</p>"
            "<p><strong>Description:</strong> %(description)s</p>"
            "<table class='table table-sm'>"
            "<thead><tr><th>Product</th><th>Qty</th><th>UoM</th></tr></thead>"
            "<tbody>%(lines)s</tbody>"
            "</table>"
        ) % {
            "requested_by": self.requested_by.name,
            "description": self.description or "-",
            "lines": lines_html,
        }

    def _on_sarabun_completed(self, document):
        """Called when sarabun document routing is completed."""
        _logger.info(
            "Sarabun completed callback for PR %s (id=%s) from document %s",
            self.name, self.id, document.name
        )
        self.button_approved()
        self.message_post(
            body=_("Approved via Sarabun document: %s") % document.name,
        )

    def _on_sarabun_rejected(self, document, recipient):
        """Called when sarabun document is rejected."""
        self.button_rejected()
        reason = recipient.comment if recipient else _("No reason provided")
        self.message_post(
            body=_("Rejected via Sarabun. Reason: %s") % reason,
        )

    def action_submit_to_sarabun(self):
        """Submit PR to Sarabun for approval routing."""
        self.ensure_one()
        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))
        self.message_post(
            body=_("Submitted to Sarabun for approval: %s") % document.name,
        )
        return document.action_select_route()

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Purchase Request report."""
        return self.env.ref("purchase_request.action_report_purchase_requests")
