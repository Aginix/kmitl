# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""
Extract assignment feature into ``disbursement_assignment``.

Retag ir.model.data rows for the assignment views, menus, security group,
and access rules from ``disbursement`` to ``disbursement_assignment`` BEFORE
Odoo's data-file cleanup phase runs (which would delete orphaned rows whose
XML IDs no longer appear in disbursement's slimmed-down manifest).

Also ensure ``disbursement_assignment`` is marked for installation so the
new module picks up the retagged records.
"""

OLD_MODULE = "disbursement"
NEW_MODULE = "disbursement_assignment"

XMLID_NAMES = [
    # security/security.xml
    "group_disbursement_verification",
    # views/disbursement_request_assignment_views.xml
    "view_disbursement_request_form_assignment",
    "view_disbursement_request_tree_assignment",
    "view_disbursement_request_search_assignment",
    # views/assignment_rule_views.xml
    "view_disbursement_assignment_rule_tree",
    "action_disbursement_assignment_rule",
    "action_apply_rules_to_pending",
    "menu_disbursement_assignment_rule",
    # views/disbursement_verification_menus.xml
    "action_disbursement_my_verifications",
    "action_disbursement_all",
    "menu_disbursement_verification",
    "menu_disbursement_my_verifications",
    "menu_disbursement_all_requests",
    # wizards/return_request_wizard_views.xml
    "disbursement_return_request_wizard_form",
    # security/ir.model.access.csv
    "access_disbursement_assignment_rule_user",
    "access_disbursement_assignment_rule_manager",
    "access_disbursement_return_request_wizard",
]


def migrate(cr, version):
    if not version:
        return

    for name in XMLID_NAMES:
        cr.execute(
            """
            UPDATE ir_model_data
               SET module = %s
             WHERE module = %s
               AND name = %s
            """,
            (NEW_MODULE, OLD_MODULE, name),
        )

    cr.execute(
        """
        INSERT INTO ir_module_module (name, state)
        VALUES (%s, 'to install')
        ON CONFLICT (name) DO UPDATE
           SET state = CASE
               WHEN ir_module_module.state = 'uninstalled'
               THEN 'to install'
               ELSE ir_module_module.state
           END
        """,
        (NEW_MODULE,),
    )
