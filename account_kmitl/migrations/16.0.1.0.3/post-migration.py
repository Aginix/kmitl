from odoo import SUPERUSER_ID, api

from odoo.addons.account_kmitl.hooks import _create_journals

# Journals renamed in this version. Existing installs created them under the
# old codes; renaming preserves their entries and avoids creating duplicates.
LEGACY_CODE_RENAMES = {"SV": "AR", "UV": "AP"}


def migrate(cr, version):
    """Rename legacy journal codes and backfill external ids on existing DBs.

    ``post_init_hook`` only runs on install, so existing databases still have
    the journals under their old codes (and without any ``ir.model.data``
    entry). Rename them first, then let the idempotent ``_create_journals``
    find the renamed journals and register their xmlids without re-creating.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref("base.main_company")

    Journal = env["account.journal"]
    for old_code, new_code in LEGACY_CODE_RENAMES.items():
        journal = Journal.search(
            [("code", "=", old_code), ("company_id", "=", company.id)], limit=1
        )
        if journal and not Journal.search_count(
            [("code", "=", new_code), ("company_id", "=", company.id)]
        ):
            journal.code = new_code

    _create_journals(env, company)
