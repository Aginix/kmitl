from odoo import _, fields, models


class SarabunStepNoteWizard(models.TransientModel):
    """Correct the ความเห็น (note) of an acted routing step."""

    _name = "sarabun.step.note.wizard"
    _description = "Edit Step Comment"

    step_id = fields.Many2one("sarabun.routing.step", required=True)
    acted_by_id = fields.Many2one(related="step_id.acted_by_id")
    note = fields.Text(string="ความเห็น")

    def action_apply(self):
        self.ensure_one()
        self.step_id._set_note(self.note)
        message = _("แก้ไขความเห็นแล้ว")
        doc = self.step_id.document_id
        # The frozen ฉบับลงนาม still prints the old comment; point at the regenerate
        # action when its module is installed.
        if doc.state == "completed" and hasattr(doc, "action_regenerate_signed_pdf"):
            message = _(
                "แก้ไขความเห็นแล้ว — ฉบับลงนาม (PDF) ยังเป็นฉบับเดิม "
                "กด สร้างไฟล์ PDF ใหม่ ในเมนูดำเนินการ"
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
