# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class SarabunDocumentRecallWizard(models.TransientModel):
    _name = "sarabun.document.recall.wizard"
    _description = "Sarabun Document Recall Wizard"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
    )
    has_actioned_recipients = fields.Boolean(
        string="Has Actioned Recipients",
        help="Some recipients have already acknowledged or approved",
    )
    reason = fields.Text(
        string="Reason for Recall",
        required=True,
        help="Explain why this document is being recalled",
    )

    # Display fields
    document_name = fields.Char(
        related="document_id.name",
        readonly=True,
    )
    document_subject = fields.Char(
        related="document_id.subject",
        readonly=True,
    )

    def action_confirm_recall(self):
        """Confirm and execute the recall"""
        self.ensure_one()

        if not self.reason or not self.reason.strip():
            raise UserError(_("Please provide a reason for recalling this document."))

        self.document_id.action_do_recall(self.reason)

        return {"type": "ir.actions.act_window_close"}

    def action_cancel(self):
        """Cancel the recall"""
        return {"type": "ir.actions.act_window_close"}
