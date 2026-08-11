from odoo import SUPERUSER_ID, api

from . import models


def post_init_hook(cr, registry):
    """Populate todo_subscribed_operating_unit_ids = assigned_operating_unit_ids
    for all existing users who have an empty subscription list.  Idempotent."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    users = env["res.users"].with_context(active_test=False).search([])
    for user in users:
        if not user.todo_subscribed_operating_unit_ids:
            user.todo_subscribed_operating_unit_ids = user.assigned_operating_unit_ids
