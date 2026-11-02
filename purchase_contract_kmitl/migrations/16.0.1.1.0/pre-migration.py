def migrate(cr, version):
    cr.execute(
        "ALTER TABLE purchase_order DROP CONSTRAINT IF EXISTS"
        " purchase_order_unique_contract_number"
    )
