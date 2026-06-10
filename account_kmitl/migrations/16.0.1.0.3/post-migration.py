from odoo import SUPERUSER_ID, api

from odoo.addons.account_kmitl.hooks import _create_journals


def migrate(cr, version):
    """Backfill external ids for journals created before xmlids were added.

    ``post_init_hook`` only runs on install, so existing databases have the 5
    KMITL journals without any ``ir.model.data`` entry. ``_create_journals`` is
    idempotent: it finds the existing journals (the chart is already loaded on a
    live database) and registers their xmlids without re-creating them.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    _create_journals(env, env.ref("base.main_company"))
