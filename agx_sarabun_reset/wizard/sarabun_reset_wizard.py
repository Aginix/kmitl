# -*- coding: utf-8 -*-
"""Reset wizard — collects the mandatory reason for the admin reset-to-draft
(ADR-0011). Mirrors sarabun.recall.wizard, the other backward-move wizard.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class SarabunResetWizard(models.TransientModel):
    _name = "sarabun.reset.wizard"
    _description = "Sarabun รีเซ็ต (Reset to Draft) Wizard"

    document_id = fields.Many2one(
        "sarabun.document", required=True, readonly=True,
    )
    reason = fields.Text(string="เหตุผล (Reason)", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.reason:
            raise UserError(_("A reason is required."))
        self.document_id.action_reset_to_draft(self.reason)
        return {"type": "ir.actions.act_window_close"}
