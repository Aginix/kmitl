from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Subscribe the หัวหน้าโครงการ of every project still open — only new or
    re-assigned managers were subscribed before."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["kmitl.project"].search(
        [
            ("manager_id", "!=", False),
            ("state", "not in", ("complete", "cancel", "rejected")),
        ]
    )._subscribe_manager()
