# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: drop the legacy Trial Balance wizard.

The Trial Balance moved from a wizard (an ``ir.actions.act_window`` opening a
transient form) to an OWL ``ir.actions.client``. Remove the obsolete
act_window and its form view up front so the menu rebinds cleanly to the new
client action when the fresh XML loads.
"""

LEGACY = (
    ("ir.actions.act_window", "action_trial_balance_wizard_kmitl"),
    ("ir.ui.view", "trial_balance_wizard_kmitl_form"),
)


def migrate(cr, version):
    # `version` is None on first install; there is nothing to clean up then.
    if not version:
        return

    for model, name in LEGACY:
        cr.execute(
            """
            SELECT id, res_id
            FROM ir_model_data
            WHERE module = 'accounting_kmitl_reports'
              AND model = %s
              AND name = %s
            """,
            (model, name),
        )
        row = cr.fetchone()
        if not row:
            continue
        imd_id, res_id = row
        if res_id:
            if model == "ir.actions.act_window":
                cr.execute("DELETE FROM ir_act_window WHERE id = %s", (res_id,))
                cr.execute("DELETE FROM ir_actions WHERE id = %s", (res_id,))
            elif model == "ir.ui.view":
                cr.execute("DELETE FROM ir_ui_view WHERE id = %s", (res_id,))
        cr.execute("DELETE FROM ir_model_data WHERE id = %s", (imd_id,))
