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
    # ลงนาม/ไม่ลงนาม ของผู้จัดทำ, asked at the send gate. No default on purpose: the
    # drafter must pick it every time (UAT feedback — a prefilled choice was sent
    # without being read).
    originator_sign_mode = fields.Selection(
        [
            ("sign", "ลงนาม — ผู้จัดทำ (เจ้าของเรื่อง) ลงนามในหนังสือ"),
            ("no_sign", "ไม่ลงนาม — จัดทำร่างเท่านั้น"),
        ],
        string="การลงนามของผู้จัดทำ",
        required=True,
    )

    def _apply_originator_sign_mode(self):
        """Pin the originator (ผู้จัดทำ) step's verb from the explicit send-time choice,
        so the drafter consciously decides ลงนาม / ไม่ลงนาม at the gate instead of
        inheriting the default silently. Only the verb is written — allowed on the
        locked originator row."""
        self.ensure_one()
        xmlid = (
            "agx_sarabun.verb_originate"
            if self.originator_sign_mode == "sign"
            else "agx_sarabun.verb_prepare"
        )
        verb = self.env.ref(xmlid, raise_if_not_found=False)
        originator = self.document_id.routing_step_ids.filtered("is_originator")[:1]
        if verb and originator and originator.verb != verb:
            originator.verb = verb

    def action_confirm(self):
        self.ensure_one()
        if self.document_id.state not in ("draft", "returned"):
            raise UserError(_("Only draft or returned documents can be sent."))
        self._apply_originator_sign_mode()
        self.document_id.action_send()
        return {"type": "ir.actions.act_window_close"}
