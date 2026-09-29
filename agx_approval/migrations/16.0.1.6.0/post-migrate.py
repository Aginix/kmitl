# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Backfill the new requesting_department_id (หน่วยงานผู้ขอ) on existing
    requests from their analytic_distribution: pick the ส่วนงาน dimension
    already reserved, since that is the closest thing an old request has to a
    requesting unit. New requests state it directly instead (D2/D3)."""
    if not version:
        return
    cr.execute(
        """
        WITH dept_keys AS (
            SELECT ar.id AS request_id, (kv.key)::int AS analytic_id
            FROM approval_request ar,
                 jsonb_object_keys(ar.analytic_distribution) AS kv(key)
            JOIN account_analytic_account aaa ON aaa.id = (kv.key)::int
            JOIN account_analytic_plan aap ON aap.id = aaa.root_plan_id
            WHERE ar.requesting_department_id IS NULL
              AND aap.code = 'departments'
        ),
        picked AS (
            SELECT DISTINCT ON (request_id) request_id, analytic_id
            FROM dept_keys
            ORDER BY request_id, analytic_id
        )
        UPDATE approval_request ar
        SET requesting_department_id = picked.analytic_id
        FROM picked
        WHERE ar.id = picked.request_id
        """
    )
    _logger.info(
        "agx_approval requesting_department_id: backfilled %s rows from "
        "analytic_distribution",
        cr.rowcount,
    )
