# -*- coding: utf-8 -*-
"""Sender withdraw wizard — collects the mandatory reason for ดึงกลับ (pull back,
keep number) or ยกเลิกการส่ง (cancel-send, void number) — ADR-0006.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class SarabunRecallWizard(models.TransientModel):
    _name = "sarabun.recall.wizard"
    _description = "Sarabun ดึงกลับ / ยกเลิกการส่ง Wizard"

    document_id = fields.Many2one(
        "sarabun.document", required=True, readonly=True,
    )
    mode = fields.Selection(
        [
            ("pull_back", "ดึงกลับ — เก็บเลข แก้ไขแล้วส่งใหม่ (Recall, keep number)"),
            ("cancel_send", "ยกเลิกการส่ง — ยกเลิกเลข ปิดเรื่อง (Cancel-send, void)"),
        ],
        string="การดำเนินการ (Action)",
        required=True,
        default="pull_back",
    )
    reason = fields.Text(string="เหตุผล (Reason)", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.reason:
            raise UserError(_("A reason is required."))
        if self.mode == "pull_back":
            self.document_id.action_pull_back(self.reason)
        else:
            self.document_id.action_recall(self.reason)
        return {"type": "ir.actions.act_window_close"}
