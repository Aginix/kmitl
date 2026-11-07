def post_init_hook(cr, registry):
    """Default the clearing journal to ใบสำคัญล้างลูกหนี้เงินยืม (CAR) when the
    chart seeded it."""
    from odoo import SUPERUSER_ID, api

    env = api.Environment(cr, SUPERUSER_ID, {})
    journal = env.ref("account_kmitl.journal_car", raise_if_not_found=False)
    if journal:
        env["res.company"].search(
            [("advance_clearing_journal_id", "=", False), ("id", "=", journal.company_id.id)]
        ).advance_clearing_journal_id = journal
