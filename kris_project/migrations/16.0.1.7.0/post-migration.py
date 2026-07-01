from odoo.tools.sql import column_exists


def migrate(cr, version):
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
    cr.execute('ALTER TABLE kris_project DROP COLUMN "extra_analytic_id"')
