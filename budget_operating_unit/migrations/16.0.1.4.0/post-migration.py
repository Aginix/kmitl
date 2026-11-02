from odoo.tools.sql import column_exists


def migrate(cr, version):
    """Carry the single Beneficiary Unit onto the new many2many.

    ``beneficiary_operating_unit_id`` (Many2one) became
    ``beneficiary_operating_unit_ids`` (Many2many) so a reservation can be
    opened to several units (budget ADR-0011 amendment). Odoo leaves the old
    column behind; copy it into the relation table, then drop it.
    """
    if not version or not column_exists(
        cr, "budget_commitment", "beneficiary_operating_unit_id"
    ):
        return
    cr.execute(
        """
        INSERT INTO budget_commitment_beneficiary_operating_unit_rel
            (commitment_id, operating_unit_id)
        SELECT id, beneficiary_operating_unit_id
          FROM budget_commitment
         WHERE beneficiary_operating_unit_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )
    cr.execute(
        "ALTER TABLE budget_commitment DROP COLUMN beneficiary_operating_unit_id"
    )
