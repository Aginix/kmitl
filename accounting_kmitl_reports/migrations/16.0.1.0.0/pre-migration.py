# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: drop legacy ir.actions.client records.

The first version of this module wired the report menus to
ir.actions.client (tag mis_report.client_action — which does not exist).
The fix is to expose them as ir.actions.act_window instead, but Odoo
refuses to change a record's model under the same xmlid, so we have to
remove the old client-action rows before the new XML loads.
"""

LEGACY_XMLIDS = (
    "action_report_pl_kmitl",
    "action_report_bs_kmitl",
    "action_report_cf_kmitl",
)


def migrate(cr, version):
    # `version` is None on first install; we only need to clean up when an
    # older version of the module already left rows behind.
    if not version:
        return

    cr.execute(
        """
        SELECT id, res_id
        FROM ir_model_data
        WHERE module = 'accounting_kmitl_reports'
          AND model = 'ir.actions.client'
          AND name IN %s
        """,
        (LEGACY_XMLIDS,),
    )
    rows = cr.fetchall()
    if not rows:
        return

    imd_ids = [r[0] for r in rows]
    action_ids = [r[1] for r in rows if r[1]]

    if action_ids:
        cr.execute("DELETE FROM ir_actions WHERE id IN %s", (tuple(action_ids),))
    cr.execute("DELETE FROM ir_model_data WHERE id IN %s", (tuple(imd_ids),))
