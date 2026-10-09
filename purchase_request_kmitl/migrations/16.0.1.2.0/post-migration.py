# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration: แยกประเภท จ้างทำของ/จ้างเหมาบริการ — root ADR-0012.

ชื่อประเภทถูกใช้ตรง ๆ ในชื่อเรื่อง พ.1 (ขอให้{ประเภท}{ประเภทค่าใช้จ่าย}) จึงต้องเป็น
วลีเดียว ``procurement_type_007`` เปลี่ยนชื่อเป็น จ้างเหมาบริการ ส่วน จ้างทำของ
(``procurement_type_012``) data XML สร้างให้เองตอน -u (xmlid ใหม่ในไฟล์ noupdate
ถูกสร้างเสมอ) แต่ชื่อของ record เดิมในไฟล์ noupdate ต้องเปลี่ยนที่นี่ — และเฉพาะเมื่อ
ยังเป็นชื่อเดิม เพื่อไม่ทับชื่อที่ admin แก้เอง ชื่อเรื่อง พ.1 ไม่ขึ้นกับชื่อประเภท
จึงไม่ถูกเขียนใหม่ย้อนหลัง
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    ptype = env.ref(
        "purchase_request_kmitl.procurement_type_007", raise_if_not_found=False
    )
    if ptype and ptype.name == "จ้างทำของ/จ้างเหมาบริการ":
        ptype.name = "จ้างเหมาบริการ"
