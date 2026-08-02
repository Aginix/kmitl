from odoo import SUPERUSER_ID, api

from odoo.addons.finance_kmitl.hooks import _setup_default_paying_account


def migrate(cr, version):
    """Set up the institute's fallback paying account on existing databases.

    ``post_init_hook`` only runs on install, so the same idempotent setup is
    replayed here: flag the account and point the company at it if that has not
    been done by hand already.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env["res.company"].search([]):
        _setup_default_paying_account(env, company)
