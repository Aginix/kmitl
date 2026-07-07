from odoo.api import Environment, SUPERUSER_ID
from odoo.tools.sql import column_exists


def post_init_copy_extra_payees(cr, registry):
    """On fresh install, seed line records from base's Many2one extra_analytic_id
    and its extra_value.
    """
    if not column_exists(cr, "kris_project", "extra_analytic_id"):
        return
    cr.execute(
        """
        SELECT id, extra_analytic_id, extra_value
        FROM kris_project
        WHERE extra_analytic_id IS NOT NULL
        """
    )
    rows = cr.fetchall()
    if not rows:
        return
    env = Environment(cr, SUPERUSER_ID, {})
    env["kris.project.extra.analytic.line"].create(
        [
            {
                "project_id": project_id,
                "analytic_account_id": analytic_id,
                "amount": extra_value or 0.0,
            }
            for project_id, analytic_id, extra_value in rows
        ]
    )
