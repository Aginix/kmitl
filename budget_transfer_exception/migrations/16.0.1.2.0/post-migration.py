from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Drop the รายการโอนซ้ำกัน (duplicate lines) rule. It ships in noupdate
    data, so removing it from the XML alone would leave the record behind with
    a method that no longer exists."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref(
        "budget_transfer_exception.budget_transfer_excep_duplicate_lines",
        raise_if_not_found=False,
    )
    if rule:
        rule.unlink()
