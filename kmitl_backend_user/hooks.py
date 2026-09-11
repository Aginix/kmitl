# Copyright 2026 Aginix Technologies
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import SUPERUSER_ID, api


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    action = env.ref(
        "kmitl_backend_user.action_contact_admin", raise_if_not_found=False
    )
    if action:
        env["res.users"].search([("action_id", "=", action.id)]).write(
            {"action_id": False}
        )
