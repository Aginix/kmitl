from odoo import _, fields, models


class SarabunSignedCapacityWizard(models.TransientModel):
    """Pick the corrected ตำแหน่ง for a signed บุคลากร step (ADR-0019)."""

    _name = "sarabun.signed.capacity.wizard"
    _description = "Correct Signed Capacity"

    step_id = fields.Many2one("sarabun.routing.step", required=True)
    employee_id = fields.Many2one(related="step_id.employee_id", string="ผู้ลงนาม")
    current_position_name = fields.Char(
        related="step_id.signed_position_name", string="ตำแหน่งที่ลงนามปัจจุบัน"
    )
    position_id = fields.Many2one(
        "sarabun.position",
        string="ตำแหน่งที่ถูกต้อง",
        required=True,
        domain="[('holder_ids', 'in', [employee_id])]",
        help="Only a Position the signer currently holds.",
    )

    def action_apply(self):
        self.ensure_one()
        self.step_id._set_signed_capacity(self.position_id)
        message = _("แก้ไขตำแหน่งที่ลงนามแล้ว")
        doc = self.step_id.document_id
        # The frozen ฉบับลงนาม still carries the old ตำแหน่ง; point at the regenerate
        # action when its module is installed.
        if doc.state == "completed" and hasattr(doc, "action_regenerate_signed_pdf"):
            message = _(
                "แก้ไขตำแหน่งที่ลงนามแล้ว — ฉบับลงนาม (PDF) ยังเป็นฉบับเดิม "
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
