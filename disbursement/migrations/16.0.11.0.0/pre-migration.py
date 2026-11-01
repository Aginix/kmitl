# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: budget control moves out of ``disbursement`` (ADR-0003).

The budget fields on ``disbursement.request`` and the ``budget.commitment``
back-links now live in the new ``disbursement_budget``. Without help, upgrading
``disbursement`` would unlink their ``ir.model.fields`` rows (dropping the
columns and their data) because the module no longer declares them.

Re-point those external ids to ``disbursement_budget`` before the module loads,
so ``disbursement`` no longer owns them, and queue the new auto-install glue
modules: ``-u`` never installs a new auto_install module by itself.
"""

NEW_MODULE = "disbursement_budget"

MOVED_XMLIDS = [
    "field_disbursement_request__budget_commitment_id",
    "field_disbursement_request__budget_account_id",
    "field_disbursement_request__is_budget_account_product_expense",
    "field_disbursement_request__budget_consumed_amount",
    "field_disbursement_request__budget_consumed_date",
    "field_disbursement_request__budget_available_to_obligate",
    "field_budget_commitment__disbursement_request_ids",
    "field_budget_commitment__disbursement_request_count",
    "view_budget_commitment_form_inherit",
]

# glue module -> modules that must already be installed for it to auto-install
GLUE_MODULES = {
    "disbursement_budget": ["budget"],
    "disbursement_sarabun_budget": ["budget", "disbursement_sarabun"],
}


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        UPDATE ir_model_data
        SET module = %s
        WHERE module = 'disbursement'
          AND name IN %s
          AND name NOT IN (SELECT name FROM ir_model_data WHERE module = %s)
        """,
        (NEW_MODULE, tuple(MOVED_XMLIDS), NEW_MODULE),
    )
    for module, requires in GLUE_MODULES.items():
        cr.execute(
            """
            SELECT count(*) FROM ir_module_module
            WHERE name IN %s AND state IN ('installed', 'to upgrade')
            """,
            (tuple(requires),),
        )
        if cr.fetchone()[0] != len(requires):
            continue
        cr.execute(
            """
            UPDATE ir_module_module SET state = 'to install'
            WHERE name = %s AND state = 'uninstalled'
            """,
            (module,),
        )
