# -*- coding: utf-8 -*-
"""Send confirmation wizard — a confirm gate before ส่งเอกสารออก (action_send)."""
from odoo import _, fields, models
from odoo.exceptions import UserError


class SarabunSendWizard(models.TransientModel):
    _name = "sarabun.send.wizard"
    _description = "Sarabun Send Confirmation Wizard"

    document_id = fields.Many2one(
        "sarabun.document", required=True, readonly=True,
    )
    sender_department_id = fields.Many2one(
        related="document_id.sender_department_id", readonly=True,
    )
    # Confirming the send is the moment "ส่งด้วยทะเบียนเล่มไหน" is decided (ADR-0011):
    # show the resolved เล่มทะเบียน and let the sender switch books before it is pinned.
    sequence_id = fields.Many2one(
        related="document_id.sequence_id",
        string="เล่มทะเบียน (Register Book)",
        readonly=False,
    )

    def action_confirm(self):
        self.ensure_one()
        if self.document_id.state not in ("draft", "returned"):
            raise UserError(_("Only draft or returned documents can be sent."))
        self.document_id.action_send()
        return {"type": "ir.actions.act_window_close"}
