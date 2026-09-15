# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: retire ``purchase_request_approval_kmitl`` and
``purchase_request_verify_state``.

ทั้งสองโมดูลถูกลบไดเรกทอรีทิ้ง — Odoo ไม่ถอนการติดตั้งให้เองเมื่อไฟล์หายไป
(``update_list()`` ข้ามโมดูลที่หาไฟล์ไม่เจอ) ir.ui.view ของมันจึงยัง active และยัง
resolve xpath ได้ ทำให้ฟอร์มมีปุ่มค้างและ statusbar_visible ถูกทับด้วยชุดเก่า

- ``purchase_request_approval_kmitl`` ถูก **ยุบ** เข้า purchase_request_kmitl
  (state to_verify, button_to_verify, _compute_is_editable, exception wizard)
  และ purchase_request_budget (_compute_is_budget_editable /
  _compute_hide_reserve_budget_button) → xmlid ที่ยังมีเจ้าของใหม่ต้องโอน
- ``purchase_request_verify_state`` ถูก **เลิกใช้** ไม่มีใครรับช่วงต่อ →
  ล้างทิ้งทั้งชุด และย้ายแถวที่ค้างอยู่ที่ state ``to_examine`` ออกก่อน
"""

MERGED_MODULE = "purchase_request_approval_kmitl"
NEW_MODULE = "purchase_request_kmitl"
RETIRED_MODULE = "purchase_request_verify_state"


def _delete_module_views(cr, module):
    """ลบ view ของโมดูลผีทิ้งจริง ๆ — ปล่อยไว้แล้ว xpath ยัง apply อยู่"""
    cr.execute(
        "SELECT id, res_id FROM ir_model_data "
        "WHERE module = %s AND model = 'ir.ui.view'",
        (module,),
    )
    for imd_id, res_id in cr.fetchall():
        if res_id:
            cr.execute("DELETE FROM ir_ui_view WHERE id = %s", (res_id,))
        cr.execute("DELETE FROM ir_model_data WHERE id = %s", (imd_id,))


def _mark_uninstalled(cr, module):
    cr.execute(
        """
        UPDATE ir_module_module SET state = 'uninstalled'
         WHERE name = %s AND state NOT IN ('uninstalled', 'uninstallable')
        """,
        (module,),
    )


def _retire_approval_kmitl(cr):
    # 1) ลบ view ค้างทิ้งจริง ๆ — re-own ไม่ได้เพราะชื่อชนกับ view ของ
    #    purchase_request_kmitl เอง
    _delete_module_views(cr, MERGED_MODULE)

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
        (NEW_MODULE, MERGED_MODULE, NEW_MODULE),
    )

    # 3) ที่เหลือคือชื่อที่ purchase_request_kmitl เป็นเจ้าของอยู่แล้ว
    #    (model_purchase_request, field_purchase_request__state) — เป็น pointer
    #    ซ้ำล้วน ๆ ลบทิ้งได้ ไม่แตะ record ที่มันชี้อยู่
    cr.execute("DELETE FROM ir_model_data WHERE module = %s", (MERGED_MODULE,))

    # 4) ปิดโมดูลผีที่ไม่มีโค้ดบนดิสก์แล้ว
    _mark_uninstalled(cr, MERGED_MODULE)


def _retire_verify_state(cr):
    # 1) ย้ายแถวที่ค้างอยู่ที่ to_examine ไป to_verify ก่อนที่ค่านั้นจะหายจาก
    #    selection — ทั้งคู่แปลว่า "ยื่นแล้ว รอผู้ตรวจ" ต่างกันแค่ว่าใครตรวจ ส่วน
    #    ondelete='set default' ของโมดูลเดิมใช้ไม่ได้: _process_ondelete อ่าน
    #    ondelete จาก field ใน registry ซึ่งไม่มี to_examine แล้ว จึงข้ามไปเฉย ๆ
    #    ปล่อยแถวค้างเป็น string นอก selection (statusbar ว่าง, state in (...) เพี้ยน)
    cr.execute(
        "UPDATE purchase_request SET state = 'to_verify' WHERE state = 'to_examine'"
    )

    # 2) ลบแถว selection ของ to_examine — reflection ไม่เก็บให้ เพราะ
    #    _update_selection ลบค่าที่หายไปเฉพาะตอน pool.ready (ไม่ใช่ตอนโหลดโมดูล)
    #    และ _process_end ก็ไม่แตะ เพราะโมดูลนี้ไม่ได้อยู่ในรายการที่ถูกอัปเดต
    cr.execute(
        """
        DELETE FROM ir_model_fields_selection
         WHERE value = 'to_examine'
           AND field_id IN (
               SELECT id FROM ir_model_fields
                WHERE model = 'purchase.request' AND name = 'state'
           )
        """
    )

    # 3) ลบ view + ฟิลด์ค้างของ res.config.settings (ไม่มีโมดูลไหนรับช่วง)
    _delete_module_views(cr, RETIRED_MODULE)
    cr.execute(
        """
        DELETE FROM ir_model_fields
         WHERE model = 'res.config.settings'
           AND name = 'purchase_request_allow_verify_state'
        """
    )
    cr.execute(
        "ALTER TABLE res_config_settings "
        "DROP COLUMN IF EXISTS purchase_request_allow_verify_state"
    )

    # 4) ค่า config ที่ฟิลด์นั้นเขียนไว้ ไม่มีใครอ่านแล้ว
    cr.execute(
        "DELETE FROM ir_config_parameter "
        "WHERE key = 'purchase_request_verification.enable_verification'"
    )

    # 5) xmlid ที่เหลือชี้ไปยัง record ที่โมดูลอื่นเป็นเจ้าของอยู่แล้ว
    #    (model_purchase_request, field_purchase_request__state) — ลบเฉพาะ pointer
    cr.execute("DELETE FROM ir_model_data WHERE module = %s", (RETIRED_MODULE,))

    _mark_uninstalled(cr, RETIRED_MODULE)


def migrate(cr, version):
    if not version:
        return

    _retire_approval_kmitl(cr)
    _retire_verify_state(cr)
