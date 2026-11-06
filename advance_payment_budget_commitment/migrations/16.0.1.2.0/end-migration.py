from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Fill the newly stored budget_commitment_id (ADR-0033). Odoo computes
    the new column while this module loads, possibly before the source's
    own budget_commitment_id field is (e.g. purchase_request_budget), so
    recompute once every module is loaded."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    loans = env["advance.payment"].search(
        [("budget_commitment_id", "=", False), ("reference", "!=", False)]
    )
    env.add_to_compute(loans._fields["budget_commitment_id"], loans)
    loans.flush_recordset()
