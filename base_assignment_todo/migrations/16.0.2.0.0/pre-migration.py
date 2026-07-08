# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
This bridge was renamed from ``procurement_assignment_todo`` to
``base_assignment_todo`` (its tag now applies to every assignment.mixin
consumer, not just procurement). Existing installations upgrade by having
the old module row rewritten in place, and its ir.model.data rows retagged.
"""


def migrate(cr, version):
    if not version:
        return
    # If the previous name is still registered, rename it. Do nothing if the
    # new name is already present (fresh install path).
    cr.execute(
        "SELECT id FROM ir_module_module WHERE name = 'procurement_assignment_todo'"
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        UPDATE ir_module_module
           SET name = 'base_assignment_todo'
         WHERE name = 'procurement_assignment_todo'
        """
    )
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'base_assignment_todo'
         WHERE module = 'procurement_assignment_todo'
        """
    )
