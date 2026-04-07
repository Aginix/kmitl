# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class DisbursementRequest(models.Model):
    _name = "disbursement.request"
    _inherit = ["disbursement.request", "sarabun.document.mixin"]

    main_sarabun_document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Main Sarabun Document",
        copy=False,
    )
    sarabun_in_progress = fields.Boolean(
        compute="_compute_sarabun_in_progress",
    )

    @api.depends("main_sarabun_document_id", "main_sarabun_document_id.state")
    def _compute_sarabun_in_progress(self):
        for rec in self:
            rec.sarabun_in_progress = (
                rec.main_sarabun_document_id
                and rec.main_sarabun_document_id.state == "sent"
            )

    def _prepare_sarabun_document_vals(self):
        """Prepare values for creating a sarabun document."""
        self.ensure_one()
        vals = super()._prepare_sarabun_document_vals()
        vals["subject"] = _("Disbursement Request: %s") % self.name
        return vals

    def action_submit_to_sarabun(self):
        """Create Sarabun document as draft and open form for user to complete."""
        self.ensure_one()
        if self.state != "submitted":
            return
        result = self.action_create_sarabun_document()
        document = self.env["sarabun.document"].browse(result.get("res_id"))
        self.main_sarabun_document_id = document
        self.message_post(
            body=_("Sarabun document created: %s") % document.name,
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document",
            "res_id": document.id,
            "view_mode": "form",
            "target": "current",
        }

    def _on_sarabun_completed(self, document):
        """Head approved in Sarabun → advance to signed."""
        _logger.info(
            "Sarabun completed for DR %s from document %s",
            self.name,
            document.name,
        )
        for record in self:
            if record.state == "submitted":
                record.action_sign()
                record.message_post(
                    body=_("Approved by head via Sarabun: %s") % document.name,
                    subtype_xmlid="mail.mt_note",
                )

    def _on_sarabun_rejected(self, document, recipient):
        """Head rejected in Sarabun → stay at submitted, clear main document."""
        reason = recipient.comment if recipient else _("No reason provided")
        for record in self:
            record.main_sarabun_document_id = False
            record.message_post(
                body=_("Rejected via Sarabun by %(user)s. Reason: %(reason)s")
                % {
                    "user": recipient.actioned_by.name if recipient else _("Unknown"),
                    "reason": reason,
                },
                subtype_xmlid="mail.mt_note",
            )

    def _get_sarabun_report_action(self):
        """Delegate report rendering to disbursement report."""
        return self.env.ref(
            "disbursement.action_report_disbursement_request",
            raise_if_not_found=False,
        )
