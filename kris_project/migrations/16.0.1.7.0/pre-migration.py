"""Pre-migration: rename the legacy ``equipment_cost_in_installment`` column.

The receipt and wizard models generalised the single "equipment cost" carved
out per installment into a "deductible cost" that any expense type can fill.
Rename the column before the new field definition loads so existing data is
preserved in place.
"""


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        ALTER TABLE kris_project_receipt
        RENAME COLUMN equipment_cost_in_installment
        TO deductible_cost_in_installment
        """
    )
