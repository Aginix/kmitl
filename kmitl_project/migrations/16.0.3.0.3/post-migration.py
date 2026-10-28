import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """วิธีดำเนินการ gained an อื่น ๆ choice that unlocks its รายละเอียด: tick it
    on every project (archived ones included) whose รายละเอียด was filled in,
    so the existing text keeps showing on the form and the proposal PDF."""
    if not version:
        return
    cr.execute(
        """
        UPDATE kmitl_project
        SET methodology_other = TRUE
        WHERE NULLIF(TRIM(methodology_detail), '') IS NOT NULL
        """
    )
    _logger.info(
        "kmitl_project: ticked วิธีดำเนินการ อื่น ๆ on %s projects with a detail",
        cr.rowcount,
    )
