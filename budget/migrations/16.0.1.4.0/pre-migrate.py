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

    # 8. Add department/source columns on header (moved from line analytics)
    cr.execute(
        "ALTER TABLE budget_commitment "
        "ADD COLUMN IF NOT EXISTS department_analytic_id INTEGER"
    )
    cr.execute(
        "ALTER TABLE budget_commitment "
        "ADD COLUMN IF NOT EXISTS source_analytic_id INTEGER"
    )

    # 9. Populate header department/source from first reserve line's analytics
    cr.execute("""
        UPDATE budget_commitment bc
        SET department_analytic_id = subq.analytic_id
        FROM (
            SELECT DISTINCT ON (bcl.commitment_id)
                bcl.commitment_id, aaa.id as analytic_id
            FROM budget_commitment_line bcl,
                 jsonb_each_text(
                     COALESCE(bcl.analytic_distribution, '{}')::jsonb
                 ) AS kv(key, value),
                 account_analytic_account aaa,
                 account_analytic_plan aap
            WHERE bcl.line_type = 'reserve'
              AND kv.key ~ '^\d+$'
              AND aaa.id = kv.key::int
              AND aap.id = aaa.root_plan_id
              AND aap.code = 'departments'
            ORDER BY bcl.commitment_id, bcl.sequence, bcl.id
        ) subq
        WHERE bc.id = subq.commitment_id
          AND bc.department_analytic_id IS NULL
    """)

    cr.execute("""
        UPDATE budget_commitment bc
        SET source_analytic_id = subq.analytic_id
        FROM (
            SELECT DISTINCT ON (bcl.commitment_id)
                bcl.commitment_id, aaa.id as analytic_id
            FROM budget_commitment_line bcl,
                 jsonb_each_text(
                     COALESCE(bcl.analytic_distribution, '{}')::jsonb
                 ) AS kv(key, value),
                 account_analytic_account aaa,
                 account_analytic_plan aap
            WHERE bcl.line_type = 'reserve'
              AND kv.key ~ '^\d+$'
              AND aaa.id = kv.key::int
              AND aap.id = aaa.root_plan_id
              AND aap.code = 'sources'
            ORDER BY bcl.commitment_id, bcl.sequence, bcl.id
        ) subq
        WHERE bc.id = subq.commitment_id
          AND bc.source_analytic_id IS NULL
    """)

    # 10. Remove department/source keys from line analytic_distribution
    cr.execute("""
        UPDATE budget_commitment_line bcl
        SET analytic_distribution = subq.new_dist
        FROM (
            SELECT bcl2.id,
                (SELECT jsonb_object_agg(kv.key, kv.value)
                 FROM jsonb_each(bcl2.analytic_distribution::jsonb) kv
                 WHERE NOT EXISTS (
                     SELECT 1
                     FROM account_analytic_account aaa
                     JOIN account_analytic_plan aap ON aap.id = aaa.root_plan_id
                     WHERE aaa.id = kv.key::int
                       AND aap.code IN ('departments', 'sources')
                 )
                ) as new_dist
            FROM budget_commitment_line bcl2
            WHERE bcl2.analytic_distribution IS NOT NULL
        ) subq
        WHERE bcl.id = subq.id
    """)

    # 11. Add is_posted and budget_move_id columns to commitment lines
    cr.execute(
        "ALTER TABLE budget_commitment_line "
        "ADD COLUMN IF NOT EXISTS is_posted BOOLEAN DEFAULT FALSE"
    )
    cr.execute(
        "ALTER TABLE budget_commitment_line "
        "ADD COLUMN IF NOT EXISTS budget_move_id INTEGER"
    )

    # 12. Update stored state: reserved/obligated → in_progress
    cr.execute("""
        UPDATE budget_commitment
        SET state = 'in_progress'
        WHERE state IN ('reserved', 'obligated')
    """)

    # 13. Update parent_state on commitment lines
    cr.execute("""
        UPDATE budget_commitment_line bcl
        SET parent_state = 'in_progress'
        FROM budget_commitment bc
        WHERE bcl.commitment_id = bc.id
          AND bcl.parent_state IN ('reserved', 'obligated')
    """)

    _logger.info(
        "Migrated commitment lines from state-based to ledger-based model"
    )
