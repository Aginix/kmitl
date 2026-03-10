# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Merge payable/receivable account columns into override_account_id."""
    if not version:
        return

    cr.execute(
        "ALTER TABLE kmitl_payment_type "
        "RENAME COLUMN payable_account_id TO override_account_id"
    )
    cr.execute(
        "UPDATE kmitl_payment_type "
        "SET override_account_id = receivable_account_id "
        "WHERE override_account_id IS NULL AND receivable_account_id IS NOT NULL"
    )
    cr.execute(
        "ALTER TABLE kmitl_payment_type DROP COLUMN receivable_account_id"
    )
    _logger.info("Merged payable/receivable into override_account_id")
