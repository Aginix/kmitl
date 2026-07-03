from odoo import SUPERUSER_ID, api

from odoo.addons.account_kmitl.hooks import JOURNALS, _create_journals

# Account added in this version; needed as the PVR journal's default account.
NEW_ACCOUNT_TEMPLATE_XMLID = "account_kmitl.a_1112000006"


def migrate(cr, version):
    """Add the new journals/account and rename journal names on existing DBs.

    ``chart._load`` and ``post_init_hook`` only run on install, so upgrades must
    replicate their effects: instantiate the newly added account from its
    (freshly loaded) template, create the new journals (PVR/PAR/CAR) while
    backfilling default and payment accounts via the idempotent
    ``_create_journals``, and rename the existing journals to the new
    "ใบสำคัญ" names.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref("base.main_company")
    Account = env["account.account"]
    Journal = env["account.journal"]

    # Instantiate the newly added account from its template.
    template = env.ref(NEW_ACCOUNT_TEMPLATE_XMLID, raise_if_not_found=False)
    if template and not Account.search_count(
        [("code", "=", template.code), ("company_id", "=", company.id)]
    ):
        Account.create(
            {
                "code": template.code,
                "name": template.name,
                "account_type": template.account_type,
                "reconcile": template.reconcile,
                "company_id": company.id,
            }
        )

    # Create the new journals, backfill default/payment accounts, register xmlids.
    _create_journals(env, company)

    # Rename existing journals to the new "ใบสำคัญ" names.
    for data in JOURNALS:
        journal = Journal.search(
            [("code", "=", data["code"]), ("company_id", "=", company.id)], limit=1
        )
        if journal and journal.name != data["name"]:
            journal.name = data["name"]
