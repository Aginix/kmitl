import logging

_logger = logging.getLogger(__name__)

_VALID_STATES = ('draft', 'reserved', 'obligated', 'done', 'cancel')


def migrate(cr, version):
    """Initialize commitment line states from their parent commitment state.

    Required before ORM recomputes the header state from lines,
    otherwise all headers would snap to 'draft' (the line default).
    """
    cr.execute("""
        ALTER TABLE budget_commitment_line
        ADD COLUMN IF NOT EXISTS state VARCHAR DEFAULT 'draft';
    """)
    cr.execute("""
        UPDATE budget_commitment_line bcl
        SET state = CASE
            WHEN bc.state IN %s THEN bc.state
            ELSE 'draft'
        END
        FROM budget_commitment bc
        WHERE bcl.commitment_id = bc.id
          AND bcl.state = 'draft'
          AND bc.state != 'draft';
    """, (_VALID_STATES,))
    _logger.info("Initialized commitment line states from parent commitments")
