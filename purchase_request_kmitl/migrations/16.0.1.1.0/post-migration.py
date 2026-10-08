# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Post-migration: เติม ``requesting_department_id`` (ส่วนงานผู้ขอ, analytic แผน
``departments``) จาก ``department_id`` (hr.department) เดิมของ OCA
``purchase_request_department`` — ADR-0009.

จับคู่ด้วย ``hr_department.code`` = ``account_analytic_account.code`` ภายใต้ root plan
``departments`` เฉพาะแผนกที่ตรงกับ analytic พอดี 1 ตัว ที่เหลือปล่อยว่าง
ให้ผู้ใช้เลือกเอง
ต้องรันก่อน uninstall ``purchase_request_department`` (column ``department_id`` ยังอยู่)
"""

import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)

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


def migrate(cr, version):
    if not version:
        return
    if not column_exists(cr, "purchase_request", "department_id") or not (
        column_exists(cr, "hr_department", "code")
    ):
        _logger.info("purchase_request.department_id not found; nothing to map")
        return
    cr.execute(
        DEPT_MAP_CTE
        + """
        UPDATE purchase_request pr
           SET requesting_department_id = m.aa_id
          FROM dept_map m
         WHERE pr.department_id = m.hr_id
           AND pr.requesting_department_id IS NULL
        """
    )
    mapped = cr.rowcount
    cr.execute(
        """
        SELECT COUNT(*) FROM purchase_request
         WHERE department_id IS NOT NULL AND requesting_department_id IS NULL
        """
    )
    unmapped = cr.fetchone()[0]
    _logger.info(
        "purchase.request requesting_department_id: %s mapped by code, "
        "%s left empty (no unique analytic department with the same code)",
        mapped,
        unmapped,
    )
