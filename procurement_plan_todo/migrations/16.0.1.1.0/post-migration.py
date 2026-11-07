from odoo import SUPERUSER_ID, api

OLD_SUMMARY = (
    "Complete the operating plan (ETAs + procurement method) before creating "
    "the purchase request"
)
NAME = "กรอกแผนการดำเนินงาน"
SUMMARY = "กรอกแผนการดำเนินงาน (กำหนดการ ETA และวิธีจัดซื้อจัดจ้าง) ก่อนสร้างใบขอซื้อ"


def migrate(cr, version):
    """The Todo type is noupdate: rewrite its English name/summary in Thai,
    on the type and on the Todos already raised with the old summary."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    act_type = env.ref(
        "procurement_plan_todo.mail_activity_procurement_plan_fill",
        raise_if_not_found=False,
    )
    if not act_type:
        return
    cr.execute(
        """
        UPDATE mail_activity_type
        SET name = jsonb_build_object('en_US', %s::text),
            summary = jsonb_build_object('en_US', %s::text)
        WHERE id = %s
        """,
        (NAME, SUMMARY, act_type.id),
    )
    cr.execute(
        "UPDATE mail_activity SET summary = %s "
        "WHERE activity_type_id = %s AND summary = %s",
        (SUMMARY, act_type.id, OLD_SUMMARY),
    )
