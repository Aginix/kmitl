# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: ``purchase.request.approval.requesting_department_id`` เปลี่ยน
comodel จาก hr.department เป็น account.analytic.account (ส่วนงานผู้ขอ) — ADR-0009.

ORM จะสร้าง FK ใหม่ไปที่ ``account_analytic_account`` แต่ไม่ตรวจค่าเดิม ถ้าปล่อยไว้
``-u`` จะ abort ด้วย ForeignKeyViolation หรือชี้ไปผิดแถว จึงต้องทำใน pre:

1. ถอด FK เดิมที่ชี้ ``hr_department``
2. แปลงค่าด้วย ``hr_department.code`` = ``account_analytic_account.code`` ภายใต้ root
   plan ``departments`` (เฉพาะที่ตรงพอดี 1 ตัว) ที่จับคู่ไม่ได้ให้เป็น NULL
"""

import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)

TABLE = "purchase_request_approval"
COLUMN = "requesting_department_id"

DEPT_MAP_CTE = """
    WITH dept_map AS (
        SELECT d.id AS hr_id, MIN(aa.id) AS aa_id
          FROM hr_department d
          JOIN account_analytic_account aa ON TRIM(aa.code) = TRIM(d.code)
          JOIN account_analytic_plan p ON p.id = aa.root_plan_id
         WHERE p.code = 'departments' AND COALESCE(TRIM(d.code), '') <> ''
         GROUP BY d.id
        HAVING COUNT(aa.id) = 1
    )
"""


def _drop_hr_department_fk(cr):
    cr.execute(
        """
        SELECT con.conname
          FROM pg_constraint con
          JOIN pg_class rel ON rel.oid = con.conrelid
          JOIN pg_class ref ON ref.oid = con.confrelid
          JOIN pg_attribute att
            ON att.attrelid = con.conrelid AND att.attnum = ANY (con.conkey)
         WHERE con.contype = 'f'
           AND rel.relname = %s
           AND att.attname = %s
           AND ref.relname = 'hr_department'
        """,
        (TABLE, COLUMN),
    )
    for (conname,) in cr.fetchall():
        cr.execute(f'ALTER TABLE {TABLE} DROP CONSTRAINT "{conname}"')


def migrate(cr, version):
    if not version or not column_exists(cr, TABLE, COLUMN):
        return
    cr.execute(
        """
        SELECT 1 FROM ir_model_fields
         WHERE model = 'purchase.request.approval' AND name = %s
           AND relation = 'hr.department'
        """,
        (COLUMN,),
    )
    if not cr.fetchone():
        return
    _drop_hr_department_fk(cr)
    has_code = column_exists(cr, "hr_department", "code")
    if has_code:
        cr.execute(
            DEPT_MAP_CTE
            + f"""
            UPDATE {TABLE} pa
               SET {COLUMN} = (
                   SELECT m.aa_id FROM dept_map m WHERE m.hr_id = pa.{COLUMN}
               )
             WHERE pa.{COLUMN} IS NOT NULL
            """
        )
    else:
        cr.execute(f"UPDATE {TABLE} SET {COLUMN} = NULL WHERE {COLUMN} IS NOT NULL")
    touched = cr.rowcount
    cr.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE {COLUMN} IS NOT NULL")
    mapped = cr.fetchone()[0]
    _logger.info(
        "purchase.request.approval %s: %s mapped by code, %s left empty",
        COLUMN,
        mapped,
        touched - mapped,
    )
