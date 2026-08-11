from . import models


def post_init_hook(env):
    """Populate todo_subscribed_operating_unit_ids = assigned_operating_unit_ids
    for all existing users who have an empty subscription list.  Idempotent."""
    users = env["res.users"].with_context(active_test=False).search([])
    for user in users:
        if not user.todo_subscribed_operating_unit_ids:
            user.todo_subscribed_operating_unit_ids = user.assigned_operating_unit_ids
