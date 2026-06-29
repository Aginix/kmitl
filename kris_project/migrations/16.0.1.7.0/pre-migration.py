import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Carry the pre-1.7.0 ``extra_value`` into the new method-selector model.

    Before 1.7.0 ``extra_value`` was a plain Monetary the officer typed in.
    From 1.7.0 it is computed from either ``extra_pct`` (percentage method)
    or ``extra_fixed_amount`` (fixed method). To preserve every existing
    figure verbatim, projects with a non-zero ``extra_value`` are migrated
    onto the fixed method with the legacy amount as the seed. Untouched
    projects fall through to the new percentage default.
    """
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'kris_project' AND column_name = 'extra_value'
        """
    )
    if not cr.fetchone():
        return

    cr.execute("ALTER TABLE kris_project ADD COLUMN IF NOT EXISTS extra_calc_type varchar")
    cr.execute("ALTER TABLE kris_project ADD COLUMN IF NOT EXISTS extra_pct double precision")
    cr.execute("ALTER TABLE kris_project ADD COLUMN IF NOT EXISTS extra_fixed_amount numeric")

    cr.execute(
        """
        UPDATE kris_project
        SET extra_calc_type = 'fixed',
            extra_fixed_amount = extra_value
        WHERE extra_value IS NOT NULL AND extra_value > 0
        """
    )
    cr.execute(
        """
        UPDATE kris_project
        SET extra_calc_type = 'percentage'
        WHERE extra_calc_type IS NULL
        """
    )
    _logger.info(
        "kris_project 16.0.1.7.0: migrated %s projects to fixed extra method",
        cr.rowcount,
    )
