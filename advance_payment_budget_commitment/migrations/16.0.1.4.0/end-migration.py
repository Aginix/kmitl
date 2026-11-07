from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Fill ส่วนงาน from the commitment: the column already exists (created
    plain by advance_payment), so Odoo does not compute it on its own."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    loans = env["advance.payment"].search([("budget_commitment_id", "!=", False)])
    env.add_to_compute(loans._fields["department_analytic_id"], loans)
    loans.flush_recordset()
