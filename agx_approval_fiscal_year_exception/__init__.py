from odoo import SUPERUSER_ID, api

from . import models


def uninstall_hook(cr, registry):
    """Hand submit-date checking back to the rule this module archived."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref(
        "agx_approval.excep_submit_date_outside_fy", raise_if_not_found=False
    )
    if rule:
        rule.active = True
