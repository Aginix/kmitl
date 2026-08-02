from odoo import SUPERUSER_ID, api

from odoo.addons.finance_kmitl.hooks import setup_paying_accounts


def migrate(cr, version):
    """Set up the main paying accounts (หัวจ่าย) on existing databases.

    ``post_init_hook`` only runs on install, so the same idempotent setup is
    replayed here: flag the accounts, point the company at the fallback, and
    give the seeded payment subjects the accounts they may pay from — leaving
    anything an administrator already configured untouched.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    setup_paying_accounts(env)
