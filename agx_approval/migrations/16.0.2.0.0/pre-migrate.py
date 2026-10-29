# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).


def migrate(cr, version):
    """ADR-0010, before the update drops what it no longer defines:

    - keep each category's products (the allowed_product_ids relation table);
      post-migrate turns them into the category's own Expense Items;
    - keep the retired actual-expense rows (approval.request.allocation, model
      removed) in a legacy table instead of letting the model's table go."""
    if not version:
        return
    cr.execute(
        """
        DO $$ BEGIN
            IF to_regclass('approval_request_allocation') IS NOT NULL
               AND to_regclass('approval_request_allocation_legacy') IS NULL THEN
                ALTER TABLE approval_request_allocation
                    RENAME TO approval_request_allocation_legacy;
            END IF;
        END $$
        """
    )
    # An archive: its foreign keys (to the request, product, partner, loan …)
    # would only block deleting those records.
    cr.execute(
        """
        DO $$ DECLARE c record; BEGIN
            IF to_regclass('approval_request_allocation_legacy') IS NOT NULL THEN
                FOR c IN
                    SELECT conname FROM pg_constraint
                    WHERE conrelid = 'approval_request_allocation_legacy'::regclass
                      AND contype = 'f'
                LOOP
                    EXECUTE format(
                        'ALTER TABLE approval_request_allocation_legacy'
                        ' DROP CONSTRAINT %I', c.conname
                    );
                END LOOP;
            END IF;
        END $$
        """
    )
    cr.execute("SELECT to_regclass('approval_category_product_product_rel')")
    if cr.fetchone()[0]:
        cr.execute(
            """
            CREATE TABLE IF NOT EXISTS agx_approval_category_product_bak AS
            SELECT approval_category_id AS category_id,
                   product_product_id AS product_id
            FROM approval_category_product_product_rel
            """
        )
