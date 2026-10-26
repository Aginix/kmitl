# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Pre-migration: request lines drop product / quantity / unit price.

A line is now just account + description + ``amount``. Before ``disbursement``
loads (and Odoo drops the old columns and makes ``account_id`` NOT NULL):

1. lines without an account take their product's expense account (product,
   then product category — what the old product onchange filled in), else the
   account sharing the product's code (budget-code products carry the GL code
   and often have no expense account);
2. ``amount`` is created and filled with ``quantity * price_unit``, the
   untaxed amount the line was worth before.
"""

from odoo import SUPERUSER_ID, api


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version or not _column_exists(
        cr, "disbursement_request_line", "product_id"
    ):
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        """
        SELECT product_id, company_id, array_agg(id)
        FROM disbursement_request_line
        WHERE account_id IS NULL AND product_id IS NOT NULL
        GROUP BY product_id, company_id
        """
    )
    for product_id, company_id, line_ids in cr.fetchall():
        product = env["product.product"].with_company(company_id).browse(product_id)
        account = (
            product.property_account_expense_id
            or product.categ_id.property_account_expense_categ_id
        )
        if not account and product.default_code:
            account = env["account.account"].search(
                [
                    ("code", "=", product.default_code),
                    ("company_id", "=", company_id),
                    ("deprecated", "=", False),
                ],
                limit=1,
            )
        if account:
            cr.execute(
                "UPDATE disbursement_request_line SET account_id = %s WHERE id IN %s",
                (account.id, tuple(line_ids)),
            )
    if not _column_exists(cr, "disbursement_request_line", "amount"):
        cr.execute("ALTER TABLE disbursement_request_line ADD COLUMN amount numeric")
        cr.execute(
            """
            UPDATE disbursement_request_line
            SET amount = COALESCE(quantity, 1.0) * COALESCE(price_unit, 0.0)
            """
        )
