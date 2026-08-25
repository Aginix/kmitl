from odoo import _, models

# Todo activity types — สายสารบรรณ. helper _schedule_todo / _clear_todo และ hook
# แบบ _<todo>_activity / _recipient / _summary สืบทอดมาจาก agx_approval_todo.
CREATE_ENDORSEMENT_ACTIVITY = (
    "agx_approval_sarabun_todo.mail_activity_create_endorsement"
)
APPROVED_FYI_ACTIVITY = "agx_approval_sarabun_todo.mail_activity_approved_fyi"
RETURNED_ACTIVITY = "agx_approval_sarabun_todo.mail_activity_returned_edit"
REJECTED_FYI_ACTIVITY = "agx_approval_sarabun_todo.mail_activity_rejected_fyi"


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # ---------------------------------------------------------------------
    # สร้างหนังสือเพื่อส่งขออนุมัติ (จองงบเสร็จ → to_send)
    # ---------------------------------------------------------------------
    def _create_endorsement_activity(self):
        return CREATE_ENDORSEMENT_ACTIVITY

    def _create_endorsement_recipient(self):
        """ผู้รับ Todo สร้างหนังสือ — ค่าเริ่มต้น = ผู้สร้างคำขอ (user_id)."""
        self.ensure_one()
        return self.user_id

    def _create_endorsement_summary(self):
        self.ensure_one()
        return _(
            "คำขออนุมัติเลขที่ %s จองงบประมาณแล้ว "
            "กรุณาสร้างหนังสือเพื่อส่งขออนุมัติ"
        ) % (self.name or "")

    def _notify_create_endorsement_todo(self):
        """เข้าสู่ to_send → แจ้ง Todo ส่วนบุคคลให้ผู้สร้าง (user_id) สร้างหนังสือ."""
        for rec in self:
            rec._schedule_todo(
                rec._create_endorsement_activity(),
                rec._create_endorsement_summary(),
                user=rec._create_endorsement_recipient(),
            )

    def _clear_create_endorsement_todo(self):
        """ออกจาก to_send (ส่งหนังสือแล้ว → sent / ดึงกลับ / ยกเลิก) → ล้าง Todo."""
        self._clear_todo(self._create_endorsement_activity())

    # ---------------------------------------------------------------------
    # แจ้ง FYI เมื่อคำขอได้รับอนุมัติจริง (→ approved จาก to_send/sent)
    # ---------------------------------------------------------------------
    def _approved_fyi_activity(self):
        return APPROVED_FYI_ACTIVITY

    def _approved_fyi_recipient(self):
        self.ensure_one()
        return self.user_id

    def _approved_fyi_summary(self):
        self.ensure_one()
        return _("คำขออนุมัติเลขที่ %s ได้รับอนุมัติแล้ว") % (self.name or "")

    def _notify_approved_fyi(self):
        """เข้าสู่ approved จากการอนุมัติจริง → แจ้ง FYI กลับผู้สร้าง.

        base.automation รัด filter_pre ไว้ที่ (to_send, sent) เท่านั้น จึงไม่ยิง
        ตอนการเงินตีกลับจาก to_disburse กลับมา approved (นั่นเป็นคนละเรื่อง —
        จัดการโดย agx_approval_disbursement_todo)."""
        for rec in self:
            rec._schedule_todo(
                rec._approved_fyi_activity(),
                rec._approved_fyi_summary(),
                user=rec._approved_fyi_recipient(),
                dedupe=False,
            )

    # ---------------------------------------------------------------------
    # ตีกลับจากสารบรรณ (sent → returned): แก้ไข + ส่งหนังสือใหม่
    # ---------------------------------------------------------------------
    def _returned_activity(self):
        return RETURNED_ACTIVITY

    def _returned_recipient(self):
        self.ensure_one()
        return self.user_id

    def _returned_summary(self):
        """ครอบทั้งผู้พิจารณาตีกลับ และผู้ส่งดึงกลับหนังสือเอง: agx_sarabun
        delegate _on_sarabun_recalled (ดึงกลับ) เข้า _on_sarabun_returned จึงได้
        sent → returned เหมือนกัน แยกไม่ได้ที่ระดับ state — ไม่ระบุว่าใครส่งกลับ
        ส่วนเหตุผล (ถ้ามี) อยู่ใน chatter ของหนังสือแล้ว."""
        self.ensure_one()
        return _(
            "คำขออนุมัติเลขที่ %s กลับมาแก้ไข "
            "กรุณาแก้ไขและส่งหนังสือใหม่"
        ) % (self.name or "")

    def _notify_returned_todo(self):
        """เข้าสู่ returned จากฝั่งสารบรรณ (ตีกลับ / ดึงกลับ) → แจ้งผู้สร้างแก้ไข.

        base.automation รัด filter_pre = sent จึงไม่ชนกับกรณีตีกลับใบเบิก
        (billed → returned) ที่ agx_approval_disbursement จัดการอยู่แล้ว."""
        for rec in self:
            rec._schedule_todo(
                rec._returned_activity(),
                rec._returned_summary(),
                user=rec._returned_recipient(),
            )

    def _clear_returned_todo(self):
        """ออกจาก returned (ส่งใหม่ / ยกเลิก) → ล้าง Todo."""
        self._clear_todo(self._returned_activity())

    # ---------------------------------------------------------------------
    # แจ้ง FYI เมื่อคำขอถูกปฏิเสธ (→ rejected)
    # ---------------------------------------------------------------------
    def _rejected_fyi_activity(self):
        return REJECTED_FYI_ACTIVITY

    def _rejected_fyi_recipient(self):
        self.ensure_one()
        return self.user_id

    def _rejected_fyi_summary(self):
        self.ensure_one()
        return _("คำขออนุมัติเลขที่ %s ถูกปฏิเสธ") % (self.name or "")

    def _notify_rejected_fyi(self):
        """เข้าสู่ rejected → แจ้ง FYI (Acknowledgement) กลับผู้สร้าง."""
        for rec in self:
            rec._schedule_todo(
                rec._rejected_fyi_activity(),
                rec._rejected_fyi_summary(),
                user=rec._rejected_fyi_recipient(),
                dedupe=False,
            )
