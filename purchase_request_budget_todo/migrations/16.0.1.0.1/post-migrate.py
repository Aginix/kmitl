from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """The reserve-budget Todo now goes to the PR-specific role จองงบประมาณ พ.1
    instead of the generic จองงบประมาณ (root ADR-0010). The automation is
    noupdate, so re-point the existing record here instead of relying on the XML
    reload. Todos already scheduled are left alone: they close when the request
    leaves to_verify_budget."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    automation = env.ref(
        "purchase_request_budget_todo.automation_pr_draft_to_verify",
        raise_if_not_found=False,
    )
    if automation:
        automation.code = (automation.code or "").replace(
            'env.ref("budget_role.role_budget_commitment"',
            'env.ref("purchase_request_budget_todo.role_pr_budget_commit"',
        )
