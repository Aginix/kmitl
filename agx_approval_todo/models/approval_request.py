from odoo import _, models

# Execution Todo raised while the request sits at to_verify (รอตรวจสอบ /
# จองงบประมาณ). Routed to the จองงบประมาณ role within the request's operating
# unit (role-in-unit, mail_activity_todo_role_unit ADR-0002).
RESERVE_BUDGET_ACTIVITY = "agx_approval_todo.mail_activity_reserve_budget"
BUDGET_COMMITMENT_ROLE = "budget_role.role_budget_commitment"


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # =====================================================================
    # โครงสร้าง Lifecycle-Todo (base) — ใช้ร่วมโดยทุกโมดูล *_todo ของสายอนุมัติ
    #
    # base.automation เป็นเพียง trigger (ประกาศบน state, แอดมินเปิด/ปิดได้) แล้ว
    # delegate เข้าเมธอด _notify_* / _clear_* ซึ่งเรียก helper กลางด้านล่าง.
    # =====================================================================
    def _schedule_todo(
        self,
        activity_xmlid,
        summary,
        user=None,
        role=None,
        operating_unit=None,
        group=None,
        dedupe=True,
    ):
        """สร้าง Todo จาก activity type (xmlid) ตามโหมดผู้รับ:

        - ``role`` + ``operating_unit`` → group Todo แบบ role-in-unit
          (mail_activity_todo_role_unit) ไม่มีผู้รับเดี่ยว.
        - ``group`` (res.groups) → fan-out เป็น Todo ส่วนบุคคลให้สมาชิก internal
          ทุกคน (ใช้กรณีหน่วยกลางที่ไม่มี role-in-unit เช่น การเงิน).
        - ``user`` → Todo ส่วนบุคคลรายคน.

        ``dedupe`` = True → ข้าม record ที่มี Todo ชนิดนี้ค้างอยู่แล้ว. คืน
        recordset ของ ``mail.activity`` ที่สร้าง เพื่อให้ override/เทสต์ต่อยอดได้."""
        act_type = self.env.ref(activity_xmlid, raise_if_not_found=False)
        activities = self.env["mail.activity"]
        if not act_type:
            return activities
        for rec in self:
            if dedupe and rec.activity_ids.filtered(
                lambda a: a.activity_type_id == act_type
            ):
                continue
            if role and operating_unit:
                activities += rec.activity_schedule(
                    activity_xmlid,
                    summary=summary,
                    responsible_role_id=role.id,
                    operating_unit_id=operating_unit.id,
                )
            elif group:
                members = group.sudo().users.filtered(
                    lambda u: u.active and not u.share
                )
                for member in members:
                    activities += rec.activity_schedule(
                        activity_xmlid, summary=summary, user_id=member.id
                    )
            elif user:
                activities += rec.activity_schedule(
                    activity_xmlid, summary=summary, user_id=user.id
                )
        return activities

    def _clear_todo(self, activity_xmlids):
        """ล้าง Todo ตาม activity type (xmlid เดียวหรือ list) บน record."""
        if not isinstance(activity_xmlids, (list, tuple)):
            activity_xmlids = [activity_xmlids]
        self.activity_unlink(activity_xmlids)

    # ---------------------------------------------------------------------
    # Reserve-budget Todo (เข้า to_verify → จองงบ)
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
        role = self.env.ref(BUDGET_COMMITMENT_ROLE, raise_if_not_found=False)
        for rec in self:
            summary = rec._reserve_budget_todo_summary()
            operating_unit = rec._reserve_budget_operating_unit()
            if role and operating_unit:
                rec._schedule_todo(
                    RESERVE_BUDGET_ACTIVITY,
                    summary,
                    role=role,
                    operating_unit=operating_unit,
                )
            else:
                rec._schedule_todo(
                    RESERVE_BUDGET_ACTIVITY, summary, user=rec.user_id
                )

    def _clear_reserve_budget_todo(self):
        """ออกจาก to_verify (จองแล้ว / ดึงกลับ / ยกเลิก) → ล้าง Todo จองงบประมาณ."""
        self._clear_todo(RESERVE_BUDGET_ACTIVITY)
