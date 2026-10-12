from odoo import SUPERUSER_ID, api

# Domain written by purchase_work_acceptance_operating_unit_access_all,
# restored on uninstall so the rules stop referencing committee fields.
ACCESS_ALL_DOMAIN = (
    "['|','|',(1, '=', 1) if user.has_group("
    "'purchase_work_acceptance_operating_unit_access_all.group_all_ou_work_acceptance')"
    " else (0, '=', 1),('operating_unit_id','=',False),"
    "('operating_unit_id','in', user.operating_unit_ids.ids)]"
)
RULES = [
    "purchase_work_acceptance_operating_unit.ir_rule_work_acceptance_operating_units",
    "purchase_work_acceptance_operating_unit."
    "ir_rule_work_acceptance_line_allowed_operating_units",
]


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid in RULES:
        rule = env.ref(xmlid, raise_if_not_found=False)
        if rule:
            rule.domain_force = ACCESS_ALL_DOMAIN
