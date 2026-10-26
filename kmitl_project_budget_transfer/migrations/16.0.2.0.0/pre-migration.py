"""Pre-migration: merge ``kmitl_project_floating_allocation`` into this module
(kmitl_project ADR-0011).

Its directory is gone, and Odoo never uninstalls a module whose files vanished
(``update_list()`` skips it), so its views would keep applying. This module now
declares the same model, fields and access under its own name.
"""

MERGED_MODULE = "kmitl_project_floating_allocation"
NEW_MODULE = "kmitl_project_budget_transfer"


def _delete_module_views(cr, module):
    """Delete the merged module's views for real; they are re-created by this
    module under new names (two of them clash with this module's own)."""
    cr.execute(
        "SELECT id, res_id FROM ir_model_data "
        "WHERE module = %s AND model = 'ir.ui.view'",
        (module,),
    )
    for imd_id, res_id in cr.fetchall():
        if res_id:
            cr.execute("DELETE FROM ir_ui_view WHERE id = %s", (res_id,))
        cr.execute("DELETE FROM ir_model_data WHERE id = %s", (imd_id,))


def migrate(cr, version):
    if not version:
        return
    _delete_module_views(cr, MERGED_MODULE)
    # Hand the remaining xmlids (the wizard model, its fields, the transfer
    # flags, the access rule) to this module before the registry reflects, so
    # they are upserted instead of duplicated.
    cr.execute(
        """
        UPDATE ir_model_data SET module = %s
         WHERE module = %s
           AND name NOT IN (SELECT name FROM ir_model_data WHERE module = %s)
        """,
        (NEW_MODULE, MERGED_MODULE, NEW_MODULE),
    )
    cr.execute("DELETE FROM ir_model_data WHERE module = %s", (MERGED_MODULE,))
    cr.execute(
        """
        UPDATE ir_module_module SET state = 'uninstalled'
         WHERE name = %s AND state NOT IN ('uninstalled', 'uninstallable')
        """,
        (MERGED_MODULE,),
    )
