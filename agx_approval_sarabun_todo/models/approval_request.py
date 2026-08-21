from odoo import _, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # =====================================================================
    # โครงสร้าง Lifecycle-Todo (จุดต่อยอด/ทดสอบ)
    #
    # base.automation เป็นเพียง trigger (ประกาศบน state, แอดมินเปิด/ปิดได้) แล้ว
    # delegate มาที่เมธอด _notify_* / _clear_* ด้านล่าง ซึ่งเป็น "ผิวสัมผัส" จริง
    # สำหรับการทดสอบและ override. เมธอด orchestrator เรียก helper กลาง
    # (_schedule_todo / _clear_todo) ผ่าน hook ย่อย 3 ตัวต่อ Todo หนึ่งชนิด:
    #
    #   _<todo>_activity()   → xmlid ของ mail.activity.type   (สลับชนิดกิจกรรม)
    #   _<todo>_recipient()  → res.users ผู้รับ                (เปลี่ยนผู้รับมอบหมาย)
    #   _<todo>_summary()    → ข้อความบน Todo                  (เปลี่ยนถ้อยคำ)
    #
    # โมดูลภายหลังจึง override เฉพาะ hook ที่ต้องการได้ โดยไม่ต้องเขียน
    # orchestrator หรือแตะ base.automation ใหม่.
    # =====================================================================

    # -- helper กลาง -------------------------------------------------------
    def _schedule_todo(self, activity_xmlid, summary, user=None, dedupe=True):
        """สร้าง Todo ส่วนบุคคลจาก activity type (xmlid) ให้ ``user``.

        ``dedupe`` = True → ข้าม record ที่มี Todo ชนิดนี้ค้างอยู่แล้ว (กันซ้ำ
        เมื่อกลับเข้าสถานะเดิม). คืน recordset ของ ``mail.activity`` ที่สร้าง
        เพื่อให้เมธอดที่ override ต่อยอด และเทสต์ assert ได้สะดวก."""
        act_type = self.env.ref(activity_xmlid, raise_if_not_found=False)
        activities = self.env["mail.activity"]
        if not act_type:
            return activities
        for rec in self:
            if not user:
                continue
            if dedupe and rec.activity_ids.filtered(
                lambda a: a.activity_type_id == act_type
            ):
                continue
            activities += rec.activity_schedule(
                activity_xmlid, summary=summary, user_id=user.id
            )
        return activities

    def _clear_todo(self, activity_xmlid):
        """ล้าง Todo ชนิดนี้ทั้งหมดบน record (ทั้งที่มี/ไม่มีผู้รับ)."""
        self.activity_unlink([activity_xmlid])

    # -- 1) สร้างหนังสือเพื่อส่งขออนุมัติ (จองงบเสร็จ → to_send) -------------
    def _create_endorsement_activity(self):
        return "agx_approval_sarabun_todo.mail_activity_create_endorsement"

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
        """เข้าสู่ to_send → แจ้งผู้สร้างให้เข้ามาสร้างหนังสือ."""
        for rec in self:
            rec._schedule_todo(
                rec._create_endorsement_activity(),
                rec._create_endorsement_summary(),
                user=rec._create_endorsement_recipient(),
            )

    def _clear_create_endorsement_todo(self):
        """ออกจาก to_send (ส่งหนังสือแล้ว → sent / ดึงกลับ / ยกเลิก) → ล้าง Todo."""
        self._clear_todo(self._create_endorsement_activity())

    # -- 2) FYI เมื่อได้รับอนุมัติ (→ approved) ----------------------------
    def _approved_fyi_activity(self):
        return "agx_approval_sarabun_todo.mail_activity_approved_fyi"

    def _approved_fyi_recipient(self):
        """ผู้รับ FYI — ค่าเริ่มต้น = ผู้สร้างคำขอ (user_id)."""
        self.ensure_one()
        return self.user_id

    def _approved_fyi_summary(self):
        self.ensure_one()
        return _("คำขออนุมัติเลขที่ %s ได้รับอนุมัติแล้ว") % (self.name or "")

    def _notify_approved_fyi(self):
        """เข้าสู่ approved → แจ้ง FYI (Acknowledgement) กลับผู้สร้าง.

        dedupe=False: แต่ละครั้งที่ได้รับอนุมัติ (รวมกรณีตีกลับแล้วอนุมัติใหม่)
        ถือเป็นเหตุการณ์ที่ควรแจ้ง — และเป็น Acknowledgement จึงปิดได้ด้วย
        'Mark as Read' รายคน ไม่ต้องมี automation ล้างให้."""
        for rec in self:
            rec._schedule_todo(
                rec._approved_fyi_activity(),
                rec._approved_fyi_summary(),
                user=rec._approved_fyi_recipient(),
                dedupe=False,
            )
