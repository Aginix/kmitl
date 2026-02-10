import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Migrate from state-based commitment lines to ledger-based (line_type).

    Converts the line-level 'state' field into ledger entries:
    - All existing lines become 'reserve' entries
    - Obligated/done lines get duplicated as 'obligate' entries
    - Cancelled lines get negative reserve entries to zero them out
    - Header control flags (is_approved, is_cancelled, is_closed) are set
    """
    # 1. Add line_type column (default='reserve')
    cr.execute(
        "ALTER TABLE budget_commitment_line "
        "ADD COLUMN IF NOT EXISTS line_type VARCHAR DEFAULT 'reserve'"
    )

    # 2. Add date column on lines
    cr.execute(
        "ALTER TABLE budget_commitment_line "
        "ADD COLUMN IF NOT EXISTS date DATE"
    )
    cr.execute("""
        UPDATE budget_commitment_line bcl
        SET date = bc.date
        FROM budget_commitment bc
        WHERE bcl.commitment_id = bc.id
          AND bcl.date IS NULL
    """)

    # 3. All existing lines become 'reserve'
    cr.execute(
        "UPDATE budget_commitment_line "
        "SET line_type = 'reserve' WHERE line_type IS NULL"
    )

    # 4. For obligated/done lines: create matching obligate entries
    cr.execute("""
        INSERT INTO budget_commitment_line (
            commitment_id, line_type, account_id, amount,
            analytic_distribution, sequence, description, date,
            currency_id, company_id, account_fiscal_year_id,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            commitment_id, 'obligate', account_id, amount,
            analytic_distribution, sequence + 1000,
            'Migrated obligation', date,
            currency_id, company_id, account_fiscal_year_id,
            create_uid, create_date, write_uid, write_date
        FROM budget_commitment_line
        WHERE state IN ('obligated', 'done')
    """)

    # 5. For cancelled lines: add negative reserve to zero them out
    cr.execute("""
        INSERT INTO budget_commitment_line (
            commitment_id, line_type, account_id, amount,
            analytic_distribution, sequence, description, date,
            currency_id, company_id, account_fiscal_year_id,
            create_uid, create_date, write_uid, write_date
        )
        SELECT
            commitment_id, 'reserve', account_id, -amount,
            analytic_distribution, sequence + 1000,
            'Migrated cancellation', date,
            currency_id, company_id, account_fiscal_year_id,
            create_uid, create_date, write_uid, write_date
        FROM budget_commitment_line
        WHERE state = 'cancel'
    """)

    # 6. Add header control flags
    cr.execute(
        "ALTER TABLE budget_commitment "
        "ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE"
    )
    cr.execute(
        "ALTER TABLE budget_commitment "
        "ADD COLUMN IF NOT EXISTS is_cancelled BOOLEAN DEFAULT FALSE"
    )
    cr.execute(
        "ALTER TABLE budget_commitment "
        "ADD COLUMN IF NOT EXISTS is_closed BOOLEAN DEFAULT FALSE"
    )
    cr.execute(
        "UPDATE budget_commitment SET is_approved = TRUE "
        "WHERE state IN ('reserved', 'obligated', 'done')"
    )
    cr.execute(
        "UPDATE budget_commitment SET is_cancelled = TRUE "
        "WHERE state = 'cancel'"
    )
    cr.execute(
        "UPDATE budget_commitment SET is_closed = TRUE "
        "WHERE state = 'done'"
    )

    # 7. Drop old state column from lines
    cr.execute(
        "ALTER TABLE budget_commitment_line "
        "DROP COLUMN IF EXISTS state"
    )

    _logger.info(
        "Migrated commitment lines from state-based to ledger-based model"
    )
