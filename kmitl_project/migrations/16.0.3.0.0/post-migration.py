import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _in_flight_transfer_analytic_ids(cr):
    """Project dimensions named on a budget transfer not yet posted, cancelled
    or rejected. Read in SQL: this runs before kmitl_project_budget_transfer
    loads its ``_has_pending_project_transfer`` override."""
    cr.execute("SELECT to_regclass('budget_transfer')")
    if not cr.fetchone()[0]:
        return set()
    cr.execute(
        """
        SELECT DISTINCT l.kmitl_project_analytic_id
        FROM budget_move_line l
        JOIN budget_transfer t ON t.move_id = l.move_id
        WHERE l.kmitl_project_analytic_id IS NOT NULL
            AND t.state NOT IN ('posted', 'cancelled', 'rejected')
        """
    )
    return {row[0] for row in cr.fetchall()}


def migrate(cr, version):
    """ยกเลิก is now the end state of a soft-deleted project (ADR-0011): archive
    the projects already cancelled — and their analytic accounts — unless they
    still hold money, including a transfer still in progress on their
    dimension, which stays visible so it can be returned (โอนคืนงบลอย)."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    in_flight = _in_flight_transfer_analytic_ids(cr)
    cancelled = env["kmitl.project"].search([("state", "=", "cancel")])
    to_archive = cancelled.filtered(
        lambda p: (
            p.analytic_account_id.id not in in_flight
            and not p._get_held_money_reasons()
        )
    )
    to_archive.write({"active": False})
    to_archive.analytic_account_id.filtered("active").write({"active": False})
    _logger.info(
        "kmitl_project: archived %s of %s cancelled projects (the rest hold money)",
        len(to_archive),
        len(cancelled),
    )
