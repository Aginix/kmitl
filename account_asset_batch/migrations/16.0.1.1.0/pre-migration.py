def migrate(cr, version):
    """Convert `received_from_agency` from Char to Many2one(res.partner).

    Preserve any existing free-text values by renaming the old column to
    `received_from_agency_legacy`; the ORM will then create the new int4
    column empty. Without this, upgrade fails on
    `ALTER COLUMN ... TYPE int4 USING ...::int4` for rows that hold text.
    """
    cr.execute(
        """
        SELECT data_type
          FROM information_schema.columns
         WHERE table_name = 'account_asset_batch'
           AND column_name = 'received_from_agency'
        """
    )
    row = cr.fetchone()
    if not row:
        return
    if row[0] == 'integer':
        return
    cr.execute(
        """
        ALTER TABLE account_asset_batch
        DROP COLUMN IF EXISTS received_from_agency_legacy
        """
    )
    cr.execute(
        """
        ALTER TABLE account_asset_batch
        RENAME COLUMN received_from_agency TO received_from_agency_legacy
        """
    )
