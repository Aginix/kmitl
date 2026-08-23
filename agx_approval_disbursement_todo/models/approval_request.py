from odoo import _, models

# Todo activity types — สายการเงิน/เบิกจ่าย. helper _schedule_todo / _clear_todo
# สืบทอดมาจาก agx_approval_todo.
RECORD_ACTUAL_ACTIVITY = "agx_approval_disbursement_todo.mail_activity_record_actual"
FINANCE_VERIFY_ACTIVITY = (
    "agx_approval_disbursement_todo.mail_activity_finance_verify"
)
BILLED_FYI_ACTIVITY = "agx_approval_disbursement_todo.mail_activity_billed_fyi"

# การเงินเป็นหน่วยกลาง (ไม่มี role-in-unit) → fan-out Todo ให้สมาชิกกลุ่มนี้.
DISBURSEMENT_OFFICER_GROUP = "disbursement.group_disbursement_officer"


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # ---------------------------------------------------------------------
    # บันทึกค่าใช้จ่ายจริง แล้วส่งการเงิน (เข้าสู่ approved)
    #
    # activity type เดียว (record_actual) แต่มี 2 ทางเข้า → 2 ข้อความ:
    #   - อนุมัติจริง (to_send/sent → approved): บันทึกค่าใช้จ่ายจริง
    #   - การเงินตีกลับ (to_disburse → approved): แก้ไขค่าใช้จ่ายจริง
    # ใช้ type เดียวกันเพื่อให้ automation "ออกจาก approved" ล้างได้ครอบทั้งคู่.
    # ---------------------------------------------------------------------
    def _record_actual_activity(self):
        return RECORD_ACTUAL_ACTIVITY

    def _record_actual_recipient(self):
        """ผู้รับ — ค่าเริ่มต้น = ผู้สร้างคำขอ (user_id)."""
        self.ensure_one()
        return self.user_id

    def _record_actual_summary(self):
        self.ensure_one()
        return _(
            "คำขออนุมัติเลขที่ %s ได้รับอนุมัติแล้ว "
            "กรุณาบันทึกค่าใช้จ่ายจริงแล้วส่งให้การเงิน"
        ) % (self.name or "")

    def _finance_return_summary(self):
        self.ensure_one()
        return _(
            "คำขออนุมัติเลขที่ %s ถูกการเงินตีกลับ "
            "กรุณาแก้ไขค่าใช้จ่ายจริงแล้วส่งให้การเงินใหม่"
        ) % (self.name or "")

    def _notify_record_actual_todo(self):
        """อนุมัติจริง (to_send/sent → approved) → แจ้งผู้สร้างบันทึกค่าใช้จ่ายจริง."""
        for rec in self:
            rec._schedule_todo(
                rec._record_actual_activity(),
                rec._record_actual_summary(),
                user=rec._record_actual_recipient(),
            )

    def _notify_finance_return_todo(self):
        """การเงินตีกลับ (to_disburse → approved) → แจ้งผู้สร้างแก้ไขค่าใช้จ่ายจริง.
        ใช้ activity type เดียวกับ record_actual (ล้างที่เดียวกัน)."""
        for rec in self:
            rec._schedule_todo(
                rec._record_actual_activity(),
                rec._finance_return_summary(),
                user=rec._record_actual_recipient(),
            )

    def _clear_record_actual_todo(self):
        """ออกจาก approved (ส่งการเงิน / ดึงกลับ draft / ยกเลิก) → ล้าง Todo."""
        self._clear_todo(self._record_actual_activity())

    # ---------------------------------------------------------------------
    # ตรวจสอบและตั้งเบิก (เข้าสู่ to_disburse) — แจ้งเจ้าหน้าที่การเงิน (กลุ่ม)
    # ---------------------------------------------------------------------
    def _finance_verify_activity(self):
        return FINANCE_VERIFY_ACTIVITY

    def _finance_verify_group(self):
        """กลุ่มผู้รับ Todo ฝั่งการเงิน — เจ้าหน้าที่เบิกจ่าย (หน่วยกลาง)."""
        return self.env.ref(DISBURSEMENT_OFFICER_GROUP, raise_if_not_found=False)

    def _finance_verify_summary(self):
        self.ensure_one()
        return _(
            "คำขออนุมัติเลขที่ %s ส่งให้การเงินแล้ว "
            "กรุณาตรวจสอบและตั้งเบิก"
        ) % (self.name or "")

    def _notify_finance_verify_todo(self):
        """เข้าสู่ to_disburse → แจ้ง Todo ให้เจ้าหน้าที่การเงินตรวจสอบและตั้งเบิก."""
        group = self._finance_verify_group()
        for rec in self:
            rec._schedule_todo(
                rec._finance_verify_activity(),
                rec._finance_verify_summary(),
                group=group,
            )

    def _clear_finance_verify_todo(self):
        """ออกจาก to_disburse (ตั้งเบิกแล้ว / ตีกลับ / ดึงกลับ) → ล้าง Todo การเงิน."""
        self._clear_todo(self._finance_verify_activity())

    # ---------------------------------------------------------------------
    # แจ้ง FYI เมื่อเบิกจ่ายแล้ว (→ billed)
    # ---------------------------------------------------------------------
    def _billed_fyi_activity(self):
        return BILLED_FYI_ACTIVITY

    def _billed_fyi_recipient(self):
        self.ensure_one()
        return self.user_id

    def _billed_fyi_summary(self):
        self.ensure_one()
        return _("คำขออนุมัติเลขที่ %s ดำเนินการเบิกจ่ายแล้ว") % (self.name or "")

    def _notify_billed_fyi(self):
        """เข้าสู่ billed → แจ้ง FYI (Acknowledgement) กลับผู้สร้าง."""
        for rec in self:
            rec._schedule_todo(
                rec._billed_fyi_activity(),
                rec._billed_fyi_summary(),
                user=rec._billed_fyi_recipient(),
                dedupe=False,
            )
