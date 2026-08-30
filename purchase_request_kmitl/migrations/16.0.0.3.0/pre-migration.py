# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: retire ``purchase_request_approval_kmitl``.

โมดูลถูกยุบเข้า purchase_request_kmitl (state to_verify, button_to_verify,
_compute_is_editable, exception wizard) และ purchase_request_budget
(_compute_is_budget_editable / _compute_hide_reserve_budget_button) แล้วลบ
ไดเรกทอรีทิ้ง — Odoo ไม่ถอนการติดตั้งให้เองเมื่อไฟล์หายไป ir.ui.view ของมันจึง
ยัง active และยัง resolve xpath ได้ ทำให้ฟอร์มมีปุ่ม button_to_verify ซ้ำและ
statusbar_visible ถูกทับด้วยชุดเก่า
"""

OLD_MODULE = "purchase_request_approval_kmitl"
NEW_MODULE = "purchase_request_kmitl"


def migrate(cr, version):
    if not version:
        return

    # 1) ลบ view ค้างทิ้งจริง ๆ — re-own ไม่ได้เพราะชื่อชนกับ view ของ
    #    purchase_request_kmitl เอง
    cr.execute(
        "SELECT id, res_id FROM ir_model_data "
        "WHERE module = %s AND model = 'ir.ui.view'",
        (OLD_MODULE,),
    )
    for imd_id, res_id in cr.fetchall():
        if res_id:
            cr.execute("DELETE FROM ir_ui_view WHERE id = %s", (res_id,))
        cr.execute("DELETE FROM ir_model_data WHERE id = %s", (imd_id,))

    # 2) โอน xmlid ที่เหลือให้ purchase_request_kmitl ก่อน reflection ของ registry
    #    ทำงาน เพื่อให้ ir.model.fields / ir.model.fields.selection ของ
    #    is_purchase_request / can_request / state__to_verify upsert ทับแถวเดิม
    #    แทนที่จะสร้างแถวซ้ำ ส่วนแถวที่ purchase_request_kmitl ไม่ได้ประกาศแล้ว
    #    (tier.definition / target.state.value เก่า) จะถูก _process_end เก็บให้
    cr.execute(
        """
        UPDATE ir_model_data SET module = %s
         WHERE module = %s
           AND name NOT IN (SELECT name FROM ir_model_data WHERE module = %s)
        """,
        (NEW_MODULE, OLD_MODULE, NEW_MODULE),
    )

    # 3) ที่เหลือคือชื่อที่ purchase_request_kmitl เป็นเจ้าของอยู่แล้ว
    #    (model_purchase_request, field_purchase_request__state) — เป็น pointer
    #    ซ้ำล้วน ๆ ลบทิ้งได้ ไม่แตะ record ที่มันชี้อยู่
    cr.execute("DELETE FROM ir_model_data WHERE module = %s", (OLD_MODULE,))

    # 4) ปิดโมดูลผีที่ไม่มีโค้ดบนดิสก์แล้ว — update_list() ของ Odoo ข้ามโมดูลที่
    #    หาไฟล์ไม่เจอ จึงไม่มีอะไรมาเปลี่ยน state ให้เอง
    cr.execute(
        """
        UPDATE ir_module_module SET state = 'uninstalled'
         WHERE name = %s AND state NOT IN ('uninstalled', 'uninstallable')
        """,
        (OLD_MODULE,),
    )
