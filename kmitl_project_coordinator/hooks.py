from odoo import SUPERUSER_ID, api

# The domain kmitl_project ships for its global OU rule. This module widens it to
# let a project's owners in from another OU (security/security.xml) and the
# widened domain references coordinator_id — restore the original on uninstall so
# the rule never points at a dropped column.
ORIGINAL_OU_RULE_DOMAIN = """[
    '|',
    ('operating_unit_id', '=', False),
    ('operating_unit_id', 'in', user.operating_unit_ids.ids)
]"""


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref(
        "kmitl_project.kmitl_project_operating_unit_rule", raise_if_not_found=False
    )
    if rule:
        rule.domain_force = ORIGINAL_OU_RULE_DOMAIN
