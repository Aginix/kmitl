# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Pre-migration: backfill operating_unit_id before it becomes required.

Remittances take the OU of their first receipt (falling back to the main
OU); receipts take their remittance's OU so submit's consistency check
still passes (falling back to the main OU).
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return

    # Remittance <- OU of its first receipt that has one
    cr.execute(
        """
        UPDATE kmitl_receipt_remittance rem
        SET operating_unit_id = (
            SELECT r.operating_unit_id
            FROM kmitl_receipt r
            WHERE r.remittance_id = rem.id
              AND r.operating_unit_id IS NOT NULL
            ORDER BY r.id
            LIMIT 1
        )
        WHERE rem.operating_unit_id IS NULL
        """
    )
    # Receipt <- OU of its remittance
    cr.execute(
        """
        UPDATE kmitl_receipt r
        SET operating_unit_id = rem.operating_unit_id
        FROM kmitl_receipt_remittance rem
        WHERE r.remittance_id = rem.id
          AND r.operating_unit_id IS NULL
          AND rem.operating_unit_id IS NOT NULL
        """
    )

    cr.execute(
        """
        SELECT res_id
        FROM ir_model_data
        WHERE module = 'operating_unit' AND name = 'main_operating_unit'
        """
    )
    row = cr.fetchone()
    if not row:
        _logger.warning(
            "operating_unit.main_operating_unit not found; receipts and "
            "remittances without an operating unit were left empty."
        )
        return
    # Everything still empty <- main OU
    cr.execute(
        "UPDATE kmitl_receipt_remittance SET operating_unit_id = %s "
        "WHERE operating_unit_id IS NULL",
        (row[0],),
    )
    _logger.info("Set main operating unit on %s remittance(s)", cr.rowcount)
    cr.execute(
        "UPDATE kmitl_receipt SET operating_unit_id = %s "
        "WHERE operating_unit_id IS NULL",
        (row[0],),
    )
    _logger.info("Set main operating unit on %s receipt(s)", cr.rowcount)
