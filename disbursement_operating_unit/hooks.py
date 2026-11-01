import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Clear the operating unit seeded on pre-existing requests.

    Odoo fills a freshly added column with the field default, so installing
    this module would stamp every historical request with the installing
    user's operating unit and hide it from every other unit. Legacy documents
    have no operating unit until someone assigns one deliberately, and the
    record rules keep those visible to everybody.
    """
    cr.execute(
        "UPDATE disbursement_request SET operating_unit_id = NULL "
        "WHERE operating_unit_id IS NOT NULL"
    )
    _logger.info("Cleared seeded operating unit on %s requests", cr.rowcount)
