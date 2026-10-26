# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

OLD_MODULE = "disbursement_assignment_kmitl"
NEW_MODULE = "disbursement_validation_assignment"


def pre_init_hook(cr):
    """Take over what the module's former name, ``disbursement_assignment_kmitl``,
    left in the database.

    The module was renamed. Model and table names are unchanged, so the assignment
    rules survive; the external ids of every record the old module owned (the
    verification group and its members, views, actions, menus, access rows) are
    reassigned to this module BEFORE its data loads, so Odoo updates those rows in
    place instead of dropping and recreating them. Nothing happens on a database
    that never had the old module.
    """
    cr.execute(
        "SELECT 1 FROM ir_module_module WHERE name = %s AND state != 'uninstalled'",
        (OLD_MODULE,),
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        UPDATE ir_model_data
        SET module = %s
        WHERE module = %s
          AND name NOT IN (SELECT name FROM ir_model_data WHERE module = %s)
        """,
        (NEW_MODULE, OLD_MODULE, NEW_MODULE),
    )
    # Retire the old module record: its code is gone and nothing it owned is left.
    cr.execute(
        "UPDATE ir_module_module SET state = 'uninstalled' WHERE name = %s",
        (OLD_MODULE,),
    )
