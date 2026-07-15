# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ["purchase.request", "sarabun.document.mixin", "portal.mixin", 'thai.date.mixin']

    # To disable tier validation
    # todo: refactor move out to individual module
    _state_from = [""]
    _state_to = [""]

    main_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Main Sarabun Document",
        copy=False,
    )

    @api.depends("state", "main_sarabun_document_id")
    def _compute_is_editable(self):
        super()._compute_is_editable()
        for rec in self:
            if rec.state == "to_approve" and not rec.main_sarabun_document_id:
                rec.is_editable = True
            if rec.main_sarabun_document_id:
                rec.is_editable = False

    @api.depends(
        "state",
        "budget_commitment_id",
        "budget_commitment_id.state",
        "main_sarabun_document_id",
    )
    def _compute_is_budget_editable(self):
        super()._compute_is_budget_editable()
        for rec in self:
            if rec.main_sarabun_document_id:
                rec.is_budget_editable = False
                continue
            if (
                rec.budget_commitment_id
                and rec.budget_commitment_id.state != "cancel"
            ):
                rec.is_budget_editable = False

    def _compute_access_url(self):
        """Compute the access URL for portal access."""
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
        """Prepare values for creating a sarabun document."""
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = self.title
        if self.department_id:
            vals["sender_department_id"] = self.department_id.id
        return vals

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
        if self.is_over_reserved_budget:
            raise UserError(self.budget_shortage_message)
        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))
        self.main_sarabun_document_id = document
        self.message_post(
            body=_("Submitted to Sarabun for approval: %s") % document.name,
        )
        # return document.action_select_route()
        return {
            "type": "ir.actions.act_window",
            "res_model": 'sarabun.document',
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_sarabun_report_action(self):
        """Delegate Sarabun report to Purchase Request report."""
        return self.env.ref("purchase_request.action_report_purchase_requests")


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    @api.depends("request_id.state", "request_id.main_sarabun_document_id")
    def _compute_is_editable(self):
        super()._compute_is_editable()
        for rec in self:
            if rec.purchase_lines:
                continue
            if (
                rec.request_id.state == "to_approve"
                and not rec.request_id.main_sarabun_document_id
            ):
                rec.is_editable = True
            if rec.request_id.main_sarabun_document_id:
                rec.is_editable = False
