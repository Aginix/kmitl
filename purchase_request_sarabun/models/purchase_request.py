# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ["purchase.request", "sarabun.document.mixin", "portal.mixin", 'thai.date.mixin']

    # Disable tier validation (sarabun is the sole approval driver — ADR-0003)
    _state_from = [""]
    _state_to = [""]

    main_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Main Sarabun Document",
        copy=False,
    )

    def _compute_access_url(self):
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/purchase_request/{request.id}"

    def _get_report_base_filename(self):
        self.ensure_one()
        return 'Purchase Request-%s' % (self.name)

    def open_preview(self):
        if self.id:
            return {
                'type': 'ir.actions.act_url',
                'url': self.access_url,
                'target': 'new',
            }

    def _prepare_sarabun_document_vals(self):
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = self.title
        if self.department_id:
            vals["sender_department_id"] = self.department_id.id
        return vals

    def _on_sarabun_completed(self, document):
        """Sarabun approval callback: branch to egp or approved based on is_egp flag."""
        _logger.info(
            "Sarabun completed callback for PR %s (id=%s) from document %s",
            self.name, self.id, document.name
        )
        if self.is_egp:
            self.write({"state": "egp"})
            self.message_post(
                body=_("อนุมัติให้จัดหาผ่าน Sarabun: %s — ต้องดำเนินการ e-GP") % document.name,
            )
        else:
            self.button_approved()
            self.message_post(
                body=_("อนุมัติให้จัดหาผ่าน Sarabun: %s") % document.name,
            )

    def _on_sarabun_rejected(self, document, recipient):
        """Sarabun rejection callback: cancel the PR and release budget."""
        reason = recipient.comment if recipient else _("No reason provided")
        self.button_rejected()
        self.message_post(
            body=_("ปฏิเสธผ่าน Sarabun. เหตุผล: %s") % reason,
        )

    def action_submit_to_sarabun(self):
        """to_submit → to_approve then open sarabun document for routing."""
        self.ensure_one()
        self.write({"state": "to_approve"})
        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))
        self.main_sarabun_document_id = document
        self.message_post(
            body=_("ส่งเรื่องเข้า Sarabun เพื่อขออนุมัติ: %s") % document.name,
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": 'sarabun.document',
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_sarabun_report_action(self):
        return self.env.ref("purchase_request.action_report_purchase_requests")
