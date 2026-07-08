# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
The disbursement assignment machinery folded into the generic
``base_assignment`` module.

Two things must happen before Odoo loads the manifests:

1. The dedicated ``disbursement.assign.officer.wizard`` model is gone —
   ``assign.officer.wizard`` from ``base_assignment`` is used instead. Since
   it is a TransientModel there is no persistent data to migrate; Odoo's
   ir.model.data cleanup pass will drop the wizard model + view + security
   rows once the manifest no longer lists them.

2. Assignment notifications used to schedule the native
   ``mail.mail_activity_data_todo`` activity type; they now schedule
   ``base_assignment.mail_activity_assignment``. Existing open activities
   with the old type and the disbursement-specific summary are re-tagged
   so ``_assignment_clear_activity`` (which now matches on type alone)
   still closes them.
"""


def migrate(cr, version):
    if not version:
        return
    # Retag open assignment To-Dos onto the new activity type. We scope by
    # summary strings the module has ever raised (procurement's constant used
    # to live here in earlier versions — hence both) so we do not touch
    # unrelated To-Dos that happen to sit on a disbursement request.
    cr.execute(
        """
        UPDATE mail_activity a
           SET activity_type_id = new_at.id
          FROM ir_model_data new_md, mail_activity_type new_at,
               ir_model_data old_md, mail_activity_type old_at
         WHERE new_md.module = 'base_assignment'
           AND new_md.name = 'mail_activity_assignment'
           AND new_md.model = 'mail.activity.type'
           AND new_md.res_id = new_at.id
           AND old_md.module = 'mail'
           AND old_md.name = 'mail_activity_data_todo'
           AND old_md.model = 'mail.activity.type'
           AND old_md.res_id = old_at.id
           AND a.activity_type_id = old_at.id
           AND a.res_model = 'disbursement.request'
           AND a.summary IN (
                'Assigned as responsible verification officer',
                'Returned for correction'
           )
        """
    )
