from odoo.tools.sql import column_exists


def post_init_copy_extra_payees(cr, registry):
    """Copy existing Many2one extra_analytic_id values from kris_project
    into the new Many2many relation table.
    """
    if not column_exists(cr, "kris_project", "extra_analytic_id"):
        return
    cr.execute(
        """
        INSERT INTO kris_project_extra_analytic_rel (kris_project_id, analytic_account_id)
        SELECT id, extra_analytic_id
        FROM kris_project
        WHERE extra_analytic_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )
