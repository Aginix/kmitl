from odoo import SUPERUSER_ID, api

# The budget.move.line OU domain budget_operating_unit_access_all writes. This
# module widens it with the department clause (security/budget_security.xml) —
# restore the access-all domain on uninstall. Keep in sync with that module.
ACCESS_ALL_MOVE_LINE_DOMAIN = (
    "['|','|','|',(1, '=', 1) if user.has_group("
    "'budget_operating_unit_access_all.group_all_ou_budget') else (0, '=', 1),"
    "('operating_unit_id','=',False),"
    "('operating_unit_id','in', user.operating_unit_ids.ids),"
    "('commitment_id.beneficiary_operating_unit_ids','in', "
    "user.operating_unit_ids.ids)]"
)


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref(
        "budget_operating_unit.ir_rule_budget_move_line_allowed_operating_units",
        raise_if_not_found=False,
    )
    if rule:
        rule.domain_force = ACCESS_ALL_MOVE_LINE_DOMAIN
