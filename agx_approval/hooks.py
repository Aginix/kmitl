import logging

_logger = logging.getLogger(__name__)


def set_approval_ok_on_non_purchase_codes(cr):
    """Mark every non-procurement code approval-eligible, preserving the
    pre-flag baseline (purchase_ok = False) on install and upgrade."""
    cr.execute(
        """
        UPDATE budget_account
        SET approval_ok = TRUE
        WHERE purchase_ok IS NOT TRUE
          AND approval_ok IS NOT TRUE
        """
    )
    _logger.info("Set approval_ok on %s non-procurement budget codes", cr.rowcount)


def post_init_hook(cr, registry):
    set_approval_ok_on_non_purchase_codes(cr)
