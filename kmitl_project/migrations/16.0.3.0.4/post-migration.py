import logging

_logger = logging.getLogger(__name__)

# Models whose data files moved from CSV to noupdate XML
MODELS = (
    "account.analytic.plan",
    "project.evaluation",
    "project.fight",
    "project.global.index",
    "project.impact",
    "project.methodology",
    "project.strategic.plan",
)


def migrate(cr, version):
    """Records first loaded from the old CSV files keep noupdate = False in
    ir_model_data. Odoo deletes such records at the end of an update when they
    are no longer in a data file (strategic plans cascade to their children),
    while a fresh install from the noupdate XML would keep them. Flag them
    noupdate so installed databases behave like fresh ones."""
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_model_data
        SET noupdate = TRUE
        WHERE module = 'kmitl_project'
        AND model IN %s
        AND noupdate IS NOT TRUE
        """,
        (MODELS,),
    )
    _logger.info("kmitl_project: set noupdate on %s CSV-loaded xmlids", cr.rowcount)
