# -*- coding: utf-8 -*-
"""The single act-on-step wizard — one UI funnel for all five dispositions,
mirroring the engine's single ``act_on_step`` entry point.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..models.sarabun_routing_step import TARGET_MODE


class SarabunStepActWizard(models.TransientModel):
    _name = "sarabun.step.act.wizard"
    _description = "Sarabun Act-on-Step Wizard"

    step_id = fields.Many2one("sarabun.routing.step", required=True, readonly=True)
    document_id = fields.Many2one(related="step_id.document_id", readonly=True)
    step_verb = fields.Many2one("sarabun.verb", related="step_id.verb", readonly=True)
    target_name = fields.Char(related="step_id.target_name", readonly=True)

    disposition = fields.Selection(
        [
            ("complete", "ดำเนินการ (Complete)"),
            ("direct", "เกษียนสั่งการ (Direct — insert next)"),
            ("delegate", "มอบหมาย (Delegate — reassign this step)"),
            ("return", "ตีกลับ (Return)"),
            ("reject", "ปฏิเสธ (Reject)"),
        ],
        required=True,
        default="complete",
    )
    note = fields.Text(string="เกษียน / Comment")

    # complete (sign capacity — P5 adds full capacity selection)
    is_sign = fields.Boolean(compute="_compute_flags")
    step_target_mode = fields.Selection(related="step_id.target_mode", readonly=True)
    signed_as_position_id = fields.Many2one(
        "sarabun.position", string="Sign As (Capacity)",
    )

    # direct / delegate target
    needs_target = fields.Boolean(compute="_compute_flags")
    target_mode = fields.Selection(TARGET_MODE, default="position")
    target_position_id = fields.Many2one("sarabun.position", string="Target Position")
    target_employee_id = fields.Many2one("hr.employee", string="Target Person (บุคลากร)")
    target_department_id = fields.Many2one(
        "hr.department", string="Target Unit",
        domain=[("is_sarabun_office", "=", True)],
    )
    new_verb = fields.Many2one(
        "sarabun.verb",
        string="Next Step Verb",
        default=lambda self: self.env.ref("agx_sarabun.verb_endorse", raise_if_not_found=False),
    )
    new_for_info = fields.Boolean(string="สำเนาเรียน (CC)")

    # return
    is_return = fields.Boolean(compute="_compute_flags")
    destination = fields.Selection(
        [("sender_restart", "กลับผู้ส่ง + เริ่มใหม่ (Sender, restart)"),
         ("resume_step", "กลับไปขั้นที่เลือก (Resume from step)")],
        default="sender_restart",
    )
    resume_step_id = fields.Many2one(
        "sarabun.routing.step", string="Resume From",
        domain="[('document_id', '=', document_id), ('id', '!=', step_id)]",
    )

    @api.depends("disposition", "step_verb")
    def _compute_flags(self):
        for w in self:
            w.is_sign = w.disposition == "complete" and w.step_verb.is_signature
            w.needs_target = w.disposition in ("direct", "delegate")
            w.is_return = w.disposition == "return"

    @api.onchange("step_id")
    def _onchange_step_id(self):
        if self.step_id and self.step_id.verb.is_signature:
            self.signed_as_position_id = self.step_id.position_id

    def action_confirm(self):
        self.ensure_one()
        # ตีกลับ / ปฏิเสธ are gating-actor moves only (ADR-0006).
        if self.disposition in ("return", "reject") and not self.step_id.gating:
            raise UserError(_(
                "Only a gating step (เห็นชอบ / ลงนาม-อนุมัติ) can be "
                "ตีกลับ (returned) or ปฏิเสธ (rejected)."
            ))
        vals = {"note": self.note}
        if self.disposition == "complete":
            vals["signed_as_position_id"] = self.signed_as_position_id.id
        elif self.disposition in ("direct", "delegate"):
            if self.target_mode == "position" and not self.target_position_id:
                raise UserError(_("Select a target Position."))
            if self.target_mode == "person" and not self.target_employee_id:
                raise UserError(_("Select a target Person (บุคลากร)."))
            if self.target_mode == "unit" and not self.target_department_id:
                raise UserError(_("Select a target Unit."))
            vals.update({
                "target_mode": self.target_mode,
                "position_id": self.target_position_id.id,
                "employee_id": self.target_employee_id.id,
                "department_id": self.target_department_id.id,
            })
            if self.disposition == "direct":
                vals.update({"verb": self.new_verb.id, "for_info": self.new_for_info})
        elif self.disposition == "return":
            if not self.note:
                raise UserError(_("Please provide a reason for returning (ตีกลับ)."))
            if self.destination == "resume_step" and not self.resume_step_id:
                raise UserError(_("Pick the step to resume from."))
            vals.update({
                "destination": self.destination,
                "resume_step_id": self.resume_step_id.id,
            })
        elif self.disposition == "reject":
            if not self.note:
                raise UserError(_("Please provide a rejection reason."))

        self.step_id.act_on_step(self.disposition, vals)
        return {"type": "ir.actions.act_window_close"}
