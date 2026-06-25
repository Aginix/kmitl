"""Post-migration: backfill ``kris.project.expense.line`` from ``equipment_cost``.

The single ``equipment_cost`` field on ``kris.project`` is replaced by a
One2many of dynamic expense lines. Convert every existing non-zero value into
an expense line that points at the seeded "ค่าครุภัณฑ์" type, then drop the
legacy column (Odoo 16 does not auto-drop removed columns).
"""

from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    equipment_type = env.ref("kris_project.expense_type_equipment", raise_if_not_found=False)
    if not equipment_type:
        # The data file should have loaded by now; bail noisily if it didn't.
        raise RuntimeError(
            "Cannot migrate equipment_cost: xmlid "
            "kris_project.expense_type_equipment is missing."
        )

    cr.execute(
        """
        SELECT id, equipment_cost
        FROM kris_project
        WHERE equipment_cost IS NOT NULL
          AND equipment_cost > 0
        """
    )
    rows = cr.fetchall()

    if rows:
        ExpenseLine = env["kris.project.expense.line"]
        ExpenseLine.create([
            {
                "project_id": project_id,
                "expense_type_id": equipment_type.id,
                "amount": amount,
            }
            for project_id, amount in rows
        ])

    cr.execute("ALTER TABLE kris_project DROP COLUMN IF EXISTS equipment_cost")
