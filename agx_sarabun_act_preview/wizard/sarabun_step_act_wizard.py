"""Preview panel for the Act-on-Step wizard.

Renders a Html summary of what the chosen disposition will do when confirmed,
so the actor can see — before clicking ดำเนินการต่อ — which step(s) become
active, who receives the next to-do, or how the document's state changes.
"""

from markupsafe import Markup, escape

from odoo import _, api, fields, models


class SarabunStepActWizard(models.TransientModel):
    _inherit = "sarabun.step.act.wizard"

    preview_html = fields.Html(
        string="ผลลัพธ์ที่จะเกิดขึ้น",
        compute="_compute_preview_html",
        sanitize=False,
    )

    @api.depends(
        "disposition",
        "destination",
        "resume_step_id",
        "target_mode",
        "target_position_id",
        "target_employee_id",
        "target_department_id",
        "new_verb",
        "new_for_info",
        "step_id",
    )
    def _compute_preview_html(self):
        for wiz in self:
            wiz.preview_html = wiz._render_preview()

    # ------------------------------------------------------------------ render
    def _render_preview(self):
        self.ensure_one()
        if not self.step_id or not self.disposition:
            return False
        renderer = {
            "complete": self._preview_complete,
            "direct": self._preview_direct,
            "delegate": self._preview_delegate,
            "return": self._preview_return,
            "reject": self._preview_reject,
        }.get(self.disposition)
        if not renderer:
            return False
        return Markup(
            '<div class="o_sarabun_act_preview alert alert-info" role="status">%s</div>'
        ) % renderer()

    # ------------------------------------------------------------- disposition
    def _preview_complete(self):
        step = self.step_id
        verb = step.verb.name or ""
        target = step.target_name or ""
        head = Markup(
            "<p><b>✅ ขั้นตอนนี้จะถูกบันทึกเป็น ‘ดำเนินการแล้ว’</b><br/>"
            "<small>%s · ผู้ดำเนินการ: %s</small></p>"
        ) % (
            escape("%s — %s" % (verb, target)),
            escape(self.env.user.name or ""),
        )
        next_steps = self._next_waiting_steps()
        if next_steps:
            items = Markup("").join(self._fmt_step(s) for s in next_steps)
            tail = Markup(
                "<p><b>➡ ขั้นถัดไปที่จะเริ่มทำงาน (Stage %d)</b></p>"
                "<ul class='mb-0'>%s</ul>"
            ) % (next_steps[0].order, items)
        elif self._would_complete_document():
            tail = Markup(
                "<p><b>🎉 ไม่มีขั้นตอนที่เหลือ</b> — เอกสารจะเปลี่ยนสถานะเป็น "
                "<b>เสร็จสิ้น (completed)</b> และบันทึกฉบับลงนามจะถูก freeze</p>"
            )
        else:
            tail = Markup(
                "<p><b>⏳ ยังไม่ไปขั้นถัดไป</b> — Stage ปัจจุบันยังมีขั้นอื่นที่ต้องรอ</p>"
            )
        return head + tail

    def _preview_direct(self):
        step = self.step_id
        new_target = self._fmt_target(
            self.target_mode,
            self.target_position_id,
            self.target_employee_id,
            self.target_department_id,
        )
        verb_name = (self.new_verb.name or _("(ยังไม่เลือก Verb)"))
        cc = _(" · สำเนาเรียน") if self.new_for_info else ""
        return Markup(
            "<p><b>✍ ขั้นนี้จะถูกบันทึกเป็น ‘เกษียนสั่งการ’</b></p>"
            "<p>จะแทรกขั้นใหม่หลังจากขั้นปัจจุบัน (Stage %d):</p>"
            "<ul class='mb-0'><li>%s — <b>%s</b>%s</li></ul>"
        ) % (
            step.order + 1,
            escape(verb_name),
            escape(new_target or _("(ยังไม่เลือกเป้าหมาย)")),
            escape(cc),
        )

    def _preview_delegate(self):
        new_target = self._fmt_target(
            self.target_mode,
            self.target_position_id,
            self.target_employee_id,
            self.target_department_id,
        )
        return Markup(
            "<p><b>👥 ขั้นนี้จะถูกมอบหมาย (Delegate)</b> — เป้าหมายใหม่:</p>"
            "<ul class='mb-0'><li>%s</li></ul>"
            "<p class='text-muted mb-0'><small>ขั้นเดิมยังคง active และ to-do "
            "ของผู้ที่ถือเดิมจะถูกยกเลิก</small></p>"
        ) % escape(new_target or _("(ยังไม่เลือกเป้าหมาย)"))

    def _preview_return(self):
        doc = self.step_id.document_id
        attempt = doc.attempt_seq or 1
        if self.destination == "resume_step" and self.resume_step_id:
            body = Markup(
                "<p>เส้นทางปัจจุบัน (attempt #%d) จะถูกเก็บเป็นประวัติ "
                "และเริ่ม attempt #%d ตั้งแต่ขั้น:</p>"
                "<ul class='mb-0'><li>%s</li></ul>"
            ) % (
                attempt,
                attempt + 1,
                escape(self.resume_step_id.name or ""),
            )
        else:
            body = Markup(
                "<p>เส้นทางปัจจุบัน (attempt #%d) จะถูกเก็บเป็นประวัติ "
                "และเริ่ม attempt #%d ใหม่ตั้งแต่ ผู้จัดทำ/ผู้ส่ง</p>"
            ) % (attempt, attempt + 1)
        return (
            Markup(
                "<p><b>↩ เอกสารจะถูก ‘ตีกลับ’</b> — "
                "สถานะใหม่: <b>returned</b></p>"
            )
            + body
        )

    def _preview_reject(self):
        doc = self.step_id.document_id
        remaining = len(
            doc.routing_step_ids.filtered(lambda s: s.state in ("waiting", "active"))
        )
        number_note = (
            Markup("<li>เลขที่หนังสือจะถูกยกเลิก (void)</li>")
            if doc.register_number_id
            else Markup("")
        )
        return Markup(
            "<p><b>🚫 เอกสารจะถูก ‘ปฏิเสธ’</b> — สถานะใหม่: <b>rejected</b></p>"
            "<ul class='mb-0'>"
            "<li>ขั้นตอนที่เหลืออีก %d ขั้นจะถูกข้าม (skipped)</li>"
            "%s"
            "</ul>"
        ) % (remaining, number_note)

    # ----------------------------------------------------------------- helpers
    def _next_waiting_steps(self):
        """Steps that would become active if this complete passes the Stage —
        the next order's waiting siblings."""
        self.ensure_one()
        step = self.step_id
        doc = step.document_id
        orders = sorted(
            {s.order for s in doc.routing_step_ids if s.order > step.order}
        )
        for order in orders:
            waiting = doc.routing_step_ids.filtered(
                lambda s, o=order: s.order == o and s.state == "waiting"
            )
            if waiting:
                return waiting.sorted("id")
        return doc.routing_step_ids.browse()

    def _would_complete_document(self):
        """True if no step at a strictly later order remains waiting/active."""
        self.ensure_one()
        step = self.step_id
        later = step.document_id.routing_step_ids.filtered(
            lambda s: s.order > step.order and s.state in ("waiting", "active")
        )
        return not later

    def _fmt_step(self, step):
        holders = ", ".join(step.preview_holder_ids.mapped("name"))
        line = Markup("<b>%s</b> — %s") % (
            step.verb.name or "",
            step.target_name or "",
        )
        if holders:
            line += Markup(
                "<br/><small class='text-muted'>ผู้ที่จะได้รับ: %s</small>"
            ) % holders
        return Markup("<li>%s</li>") % line

    def _fmt_target(self, mode, position, employee, department):
        if mode == "position" and position:
            return position.display_name
        if mode == "person" and employee:
            return employee.display_name
        if mode == "unit" and department:
            return department.display_name
        return ""
