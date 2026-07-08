# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
The assignment machinery (mixin, template, wizard, activity type) moved out
of ``procurement_assignment_kmitl`` into a new ``base_assignment`` module.

Before Odoo loads the manifests, retag the existing ``ir.model.data`` row so
the activity-type record is now owned by ``base_assignment``. If we skip
this, Odoo would either try to re-create the record under the new module
and hit a name collision, or delete the "orphaned" one during cleanup.

Ownership of the wizard model/view moves too, but those have no persistent
data of their own; the ir.model.data cleanup phase moves the metadata rows
automatically. The activity type is the only record with rows outside
ir.model.data (``mail_activity`` FK-references it) that has to survive.
"""


def migrate(cr, version):
    if not version:
        return
    # activity type: procurement_assignment_kmitl.mail_activity_assignment
    #             -> base_assignment.mail_activity_assignment
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'base_assignment'
         WHERE module = 'procurement_assignment_kmitl'
           AND model  = 'mail.activity.type'
           AND name   = 'mail_activity_assignment'
        """
    )
