import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# (relation table, comodel column, detail column, อื่น ๆ xmlid)
OTHER_CHOICES = [
    (
        "kmitl_project_project_methodology_rel",
        "project_methodology_id",
        "methodology_detail",
        "kmitl_project.methodology_other",
    ),
    (
        "kmitl_project_project_evaluation_rel",
        "project_evaluation_id",
        "evaluation_detail",
        "kmitl_project.evaluation_other",
    ),
]


def migrate(cr, version):
    """วิธีดำเนินการ and วิธีการ/เครื่องมือติดตามและประเมินผล gained an อื่น ๆ
    choice that unlocks their รายละเอียด: tick it on every project (archived
    ones included) whose รายละเอียด was filled in, so the existing text keeps
    showing on the form and the proposal PDF."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for relation, column, detail, xmlid in OTHER_CHOICES:
        cr.execute(
            f"""
            INSERT INTO {relation} (kmitl_project_id, {column})
            SELECT id, %s
            FROM kmitl_project
            WHERE NULLIF(TRIM({detail}), '') IS NOT NULL
            ON CONFLICT DO NOTHING
            """,
            (env.ref(xmlid).id,),
        )
        _logger.info(
            "kmitl_project: ticked %s on %s projects with a %s",
            xmlid,
            cr.rowcount,
            detail,
        )
