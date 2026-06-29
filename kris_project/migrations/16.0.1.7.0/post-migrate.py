import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Move project attachments from Many2many relation table to One2many."""
    if not version:
        return
    cr.execute(
        """
        SELECT project_id, attachment_id
        FROM kris_project_attachment_rel
        """
    )
    rows = cr.fetchall()
    if not rows:
        _logger.info("No existing project attachments to migrate.")
        return
    _logger.info("Migrating %d project attachment links to One2many.", len(rows))
    for project_id, attachment_id in rows:
        cr.execute(
            """
            UPDATE ir_attachment
            SET res_model = 'kris.project', res_id = %s
            WHERE id = %s
              AND (res_model IS NULL OR res_model = '' OR res_model = 'kris.project')
            """,
            (project_id, attachment_id),
        )
    _logger.info("Project attachment migration complete.")
