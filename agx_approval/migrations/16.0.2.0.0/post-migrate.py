# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# The travel/training products named this were the pick-list's catch-all; they
# become the category's อื่น ๆ (typed name) instead of an Expense Item.
OTHER_PRODUCT_NAME = "ค่าใช้จ่ายอื่น ๆ"


def _product_name(env, product_id):
    return env["product.product"].browse(product_id).with_context(lang="en_US").name


def migrate(cr, version):
    """ADR-0010: categories own Expense Items instead of products, and the
    request ends at approval.

    - multi-product categories itemize; their products become Expense Items
      (unless the module data already created them), the catch-all product
      becomes อื่น ๆ;
    - plan lines of those categories name the matching item (อื่น ๆ with the
      product's name typed in for the catch-all);
    - requests in the retired to_disburse / billed states go back to approved:
      open for disbursement, for finance to close.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Item = env["approval.category.expense.item"].with_context(active_test=False)

    # multi_product is dropped at the end of this update; on a re-run it is gone.
    cr.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name = 'approval_category' AND column_name = 'multi_product'"
    )
    if cr.fetchone():
        cr.execute(
            "UPDATE approval_category SET has_expense_items = TRUE"
            " WHERE multi_product IS TRUE"
        )
    products_by_category = {}
    cr.execute("SELECT to_regclass('agx_approval_category_product_bak')")
    if cr.fetchone()[0]:
        cr.execute(
            "SELECT category_id, product_id FROM agx_approval_category_product_bak"
        )
        for category_id, product_id in cr.fetchall():
            products_by_category.setdefault(category_id, []).append(product_id)

    categories = env["approval.category"].with_context(active_test=False).search(
        [("has_expense_items", "=", True)]
    )
    categories.invalidate_recordset(["has_expense_items"])
    for category in categories:
        regular = Item.search(
            [("category_id", "=", category.id), ("is_other", "=", False)]
        )
        if not regular:
            seq = 10
            for product_id in products_by_category.get(category.id, []):
                name = _product_name(env, product_id)
                if name == OTHER_PRODUCT_NAME:
                    continue
                Item.create({"category_id": category.id, "name": name, "sequence": seq})
                seq += 10
    env["approval.category"].with_context(active_test=False).search(
        []
    )._sync_other_expense_item()

    # Plan lines of itemized categories: product -> item of the same name.
    cr.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_name = 'approval_request_line' AND column_name = 'product_id'"
    )
    rows = []
    if cr.fetchone():  # approval_request_line.product_id, gone on a re-run
        cr.execute(
            """
            SELECT l.id, l.product_id, r.category_id
            FROM approval_request_line l
            JOIN approval_request r ON r.id = l.request_id
            JOIN approval_category c ON c.id = r.category_id
            WHERE c.has_expense_items AND l.expense_item_id IS NULL
              AND l.product_id IS NOT NULL
            """
        )
        rows = cr.fetchall()
    for line_id, product_id, category_id in rows:
        category = env["approval.category"].browse(category_id)
        name = _product_name(env, product_id)
        items = Item.search([("category_id", "=", category_id)])
        item = items.filtered(lambda i: not i.is_other and i.name == name)[:1]
        vals = {"expense_item_id": item.id}
        if not item:
            vals = {
                "expense_item_id": category._other_expense_item().id,
                "other_name": name,
            }
        # SQL: the plan is locked on most of these requests (no ORM write).
        cr.execute(
            "UPDATE approval_request_line SET expense_item_id = %s, other_name = %s"
            " WHERE id = %s",
            (vals["expense_item_id"] or None, vals.get("other_name"), line_id),
        )
    env.invalidate_all()
    lines = env["approval.request.line"].search([])
    env.add_to_compute(lines._fields["name"], lines)
    lines.flush_recordset()

    cr.execute(
        "UPDATE approval_request SET state = 'approved'"
        " WHERE state IN ('to_disburse', 'billed')"
    )
    _logger.info("Moved %s approval requests back to approved", cr.rowcount)
    cr.execute("DROP TABLE IF EXISTS agx_approval_category_product_bak")
