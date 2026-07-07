# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: absorb ``disbursement_assignment_kmitl`` into ``disbursement``.

The assignment feature (model ``disbursement.assignment.rule``, the verification
group, the assign-officer wizard, and the ``disbursement.request`` extensions)
moved from the standalone module ``disbursement_assignment_kmitl`` into
``disbursement``. Model/table names are unchanged, so the
``disbursement_assignment_rule`` rows survive automatically.

Reassign the external ids of every record the old module owned to
``disbursement`` BEFORE the new disbursement XML loads, so Odoo updates those
rows in place instead of dropping and recreating them. This preserves the
verification group's user membership and the assignment-rule rows. Because
``disbursement`` is upgraded before its (removed) dependent, this runs first.
"""

OLD_MODULE = "disbursement_assignment_kmitl"
NEW_MODULE = "disbursement"
OLD_PARAM = "disbursement_assignment_kmitl.allow_takeover_assigned"
NEW_PARAM = "disbursement.allow_takeover_assigned"


def migrate(cr, version):
    # Nothing to migrate on a fresh install.
    if not version:
        return

    # Reassign xmlid ownership (groups, models, fields, views, actions, menus,
    # ACL rows) to disbursement, skipping any name disbursement already owns.
    cr.execute(
        """
        UPDATE ir_model_data
        SET module = %s
        WHERE module = %s
          AND name NOT IN (
              SELECT name FROM ir_model_data WHERE module = %s
          )
        """,
        (NEW_MODULE, OLD_MODULE, NEW_MODULE),
    )

    # Preserve any explicitly-set takeover parameter under the new key.
    cr.execute(
        "UPDATE ir_config_parameter SET key = %s WHERE key = %s",
        (NEW_PARAM, OLD_PARAM),
    )

    # Retire the now-empty module record so it does not linger as an
    # "installed" module whose code has been removed. Its data now belongs to
    # disbursement, so flipping the state here is non-destructive (no uninstall
    # hooks run, and there is nothing left owned by the old module to drop).
    cr.execute(
        """
        UPDATE ir_module_module
        SET state = 'uninstalled'
        WHERE name = %s AND state NOT IN ('uninstalled', 'uninstallable')
        """,
        (OLD_MODULE,),
    )
