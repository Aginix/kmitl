import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """วิธีดำเนินการ gained an อื่น ๆ choice that unlocks its รายละเอียด: tick it
    on every project (archived ones included) whose รายละเอียด was filled in,
    so the existing text keeps showing on the form and the proposal PDF."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    other = env.ref("kmitl_project.methodology_other")
    cr.execute(
        """
        INSERT INTO kmitl_project_project_methodology_rel
            (kmitl_project_id, project_methodology_id)
        SELECT id, %s
        FROM kmitl_project
        WHERE NULLIF(TRIM(methodology_detail), '') IS NOT NULL
        ON CONFLICT DO NOTHING
        """,
        (other.id,),
    )
    _logger.info(
        "kmitl_project: ticked วิธีดำเนินการ อื่น ๆ on %s projects with a detail",
        cr.rowcount,
    )
