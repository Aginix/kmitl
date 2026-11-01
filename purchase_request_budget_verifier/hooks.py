from odoo import SUPERUSER_ID, api

BROADCAST = "purchase_request_budget_todo.automation_pr_draft_to_verify"


def _set_broadcast(cr, active):
    """Switch the role จองงบประมาณ พ.1 ∩ OU reserve Todo (root ADR-0012).

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
