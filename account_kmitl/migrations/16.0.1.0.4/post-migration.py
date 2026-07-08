from odoo import SUPERUSER_ID, api

from odoo.addons.account_kmitl.hooks import _register_account_xmlids


def migrate(cr, version):
    """Backfill company-independent account external ids on existing DBs.

    ``post_init_hook`` only runs on install, so existing databases have the real
    accounts but no ``account_kmitl.account_<code>`` external ids. Re-run the
    idempotent registration to publish them before downstream modules reload
    their data files with ``ref="account_kmitl.account_..."``.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _register_account_xmlids(env, env.ref("base.main_company"))
