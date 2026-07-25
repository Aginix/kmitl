# -*- coding: utf-8 -*-
"""ตีกลับ (return-without-sign) wizard — collects the mandatory reason before
sending a circulating document to `returned` without stamping any step."""
from odoo import _, fields, models
from odoo.exceptions import UserError


class SarabunReturnWizard(models.TransientModel):
    _name = "sarabun.return.wizard"
    _description = "Sarabun ตีกลับ (Return without sign) Wizard"

    document_id = fields.Many2one(
        "sarabun.document", required=True, readonly=True,
    )
    reason = fields.Text(string="เหตุผลการตีกลับ (Reason)", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.reason:
            raise UserError(_("A reason is required."))
        self.document_id.action_return_no_sign(self.reason)
        return {"type": "ir.actions.act_window_close"}
