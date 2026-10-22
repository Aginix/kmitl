import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """ยกเลิก is now the end state of a soft-deleted project (ADR-0011): archive
    the projects already cancelled — and their analytic accounts — unless they
    still hold money, which stays visible so it can be returned (โอนคืนงบลอย)."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cancelled = env["kmitl.project"].search([("state", "=", "cancel")])
    to_archive = cancelled.filtered(lambda p: not p._get_held_money_reasons())
    to_archive.write({"active": False})
    to_archive.analytic_account_id.filtered("active").write({"active": False})
    _logger.info(
        "kmitl_project: archived %s of %s cancelled projects (the rest hold money)",
        len(to_archive),
        len(cancelled),
    )
