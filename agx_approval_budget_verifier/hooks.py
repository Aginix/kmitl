from odoo import SUPERUSER_ID, api

BROADCAST = "agx_approval_budget_todo.automation_notify_reserve_budget"


def _set_broadcast(cr, active):
    """Switch the role จองงบประมาณ ∩ OU reserve Todo.

    The named ผู้ยืนยันงบประมาณ gets a personal Todo instead; the automation is
    noupdate in its own module, so it is toggled here rather than edited."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    automation = env.ref(BROADCAST, raise_if_not_found=False)
    if automation:
        automation.active = active


def post_init_hook(cr, registry):
    _set_broadcast(cr, False)


def uninstall_hook(cr, registry):
    _set_broadcast(cr, True)
