from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Post every existing reservation's history to the budget ledger.

    An end-migration: it runs once every module is loaded, so the event moves
    get what the modules on top of ``budget`` add (e.g. the operating unit).

    Reports mismatches (log + ``budget.ledger_backfill_mismatch_commitment_ids``
    + the reconciliation menu) instead of aborting the upgrade (ADR-0016, Q11).
    """
    if not version:
        return
    env = api.Environment(
        cr,
        SUPERUSER_ID,
        {
            "tracking_disable": True,
            "mail_create_nolog": True,
            "mail_notrack": True,
            "budget_ledger_posting": True,
        },
    )
    env["budget.commitment"]._ledger_backfill()
