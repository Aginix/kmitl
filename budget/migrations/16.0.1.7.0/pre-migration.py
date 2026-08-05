def migrate(cr, version):
    """Backfill budget_commitment.title before it becomes required.

    Runs before the module is loaded, so the column may not exist yet: a database
    still on 16.0.1.5.3 never had ``title`` at all, while one already on
    16.0.1.6.0 has it nullable. Create it if missing, then fill every empty row —
    otherwise the NOT NULL that Odoo adds right after this silently fails to
    apply (it logs a warning and leaves the column nullable) and the field is
    required in the UI only.

    ``description`` is the best source: it already holds the human name for every
    commitment created so far — procurement.plan stamps its ชื่อรายการ there and
    kmitl.project its project name, while ``ref`` holds their *codes* (the plan's
    รหัสเอกสาร, the project's key). Falls through to ``ref`` and finally ``name``,
    which is never null, so no row can be left violating the constraint.
    """
    cr.execute(
        "ALTER TABLE budget_commitment ADD COLUMN IF NOT EXISTS title varchar"
    )
    cr.execute(
        """
        UPDATE budget_commitment
           SET title = COALESCE(
                   NULLIF(BTRIM(SPLIT_PART(description, E'\\n', 1)), ''),
                   NULLIF(BTRIM(ref), ''),
                   name
               )
         WHERE title IS NULL OR BTRIM(title) = ''
        """
    )
