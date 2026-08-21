from odoo import _, models

# Execution Todo raised while the request sits at to_verify (รอตรวจสอบ /
# จองงบประมาณ). Routed to the จองงบประมาณ role within the requester's operating
# unit (role-in-unit, mail_activity_todo_role_unit ADR-0002).
RESERVE_BUDGET_ACTIVITY = "agx_approval_todo.mail_activity_reserve_budget"
BUDGET_COMMITMENT_ROLE = "budget_role.role_budget_commitment"


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # ---------------------------------------------------------------------
    # Reserve-budget Todo — driven by base.automation on the state field, so it
    # fires on every path that lands the request at to_verify (button, bridge,
    # Sarabun) and clears on every path that leaves it (reserve → to_send,
    # ดึงกลับ → draft, ยกเลิก → rejected).
    # ---------------------------------------------------------------------
    def _reserve_budget_todo_summary(self):
        """ข้อความบน Todo — ระบุเลขที่คำขอเพื่อให้ผู้รับเห็นว่าเป็นเอกสารใด."""
        self.ensure_one()
        return _("คำขออนุมัติเลขที่ %s รอตรวจสอบและจองงบประมาณ") % (self.name or "")

    def _reserve_budget_operating_unit(self):
        """หน่วยงานที่ใช้ route group Todo จองงบประมาณ.

        ใช้ OU ของ "ใบคำขอ" เอง (`operating_unit_id`, เพิ่มโดย
        agx_approval_operating_unit) เป็นหลัก — เป็นหน่วยงานที่เอกสารสังกัดจริง
        และเป็นฟิลด์ที่ mail_activity_todo_role_unit คอยซิงก์ OU ของ Todo ที่
        เปิดค้างให้ตามเมื่อ OU ของคำขอเปลี่ยน. ตกไปใช้ OU ตั้งต้นของผู้ขอเมื่อ
        ยังไม่ติดตั้งโมดูล OU (guard ไว้จึงไม่เพิ่ม hard dependency)."""
        self.ensure_one()
        if "operating_unit_id" in self._fields and self.operating_unit_id:
            return self.operating_unit_id
        return self.user_id.default_operating_unit_id

    def _notify_reserve_budget_todo(self):
        """เข้าสู่ to_verify → แจ้ง Todo ให้เจ้าหน้าที่ role จองงบประมาณ
        ภายในหน่วยงานของคำขอเข้ามาตรวจสอบและจองงบประมาณ.

        กรณีไม่มีหน่วยงาน/ไม่พบ role ก็ตกลงมาเป็น Todo ส่วนบุคคลของผู้ขอ
        เพื่อไม่ให้งานค้างเงียบ (แนวเดียวกับ purchase_request_todo)."""
        act_type = self.env.ref(RESERVE_BUDGET_ACTIVITY, raise_if_not_found=False)
        role = self.env.ref(BUDGET_COMMITMENT_ROLE, raise_if_not_found=False)
        if not act_type:
            return
        for rec in self:
            # เข้า to_verify ผ่าน base.automation จึงยิงครั้งเดียวต่อการเปลี่ยน
            # สถานะ — กันซ้ำเผื่อกลับเข้าสถานะเดิมโดยยังไม่ถูกล้าง.
            if rec.activity_ids.filtered(lambda a: a.activity_type_id == act_type):
                continue
            summary = rec._reserve_budget_todo_summary()
            operating_unit = rec._reserve_budget_operating_unit()
            if role and operating_unit:
                rec.activity_schedule(
                    RESERVE_BUDGET_ACTIVITY,
                    summary=summary,
                    responsible_role_id=role.id,
                    operating_unit_id=operating_unit.id,
                )
            elif rec.user_id:
                rec.activity_schedule(
                    RESERVE_BUDGET_ACTIVITY,
                    summary=summary,
                    user_id=rec.user_id.id,
                )

    def _clear_reserve_budget_todo(self):
        """ออกจาก to_verify (จองแล้ว / ดึงกลับ / ยกเลิก) → ล้าง Todo จองงบประมาณ."""
        self.activity_unlink([RESERVE_BUDGET_ACTIVITY])
