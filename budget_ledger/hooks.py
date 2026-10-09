from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Post every existing reservation's history to the budget ledger.

    Reports mismatches (log + ``budget_ledger.backfill_mismatch_commitment_ids``
    + the reconciliation menu) instead of aborting the install (ADR-0016, Q11).
    """
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
