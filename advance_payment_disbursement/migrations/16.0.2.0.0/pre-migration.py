"""Pre-migration for 16.0.2.0.0 (disbursement ADR-0009).

The loan moves from the request to its เงินยืม lines: every line of a request
that was of payment type advance takes the request's loan. The header column is
dropped by the ORM at the end of the update.
"""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        ALTER TABLE disbursement_request_line
            ADD COLUMN IF NOT EXISTS advance_payment_id integer
        """
    )
    cr.execute(
        """
        UPDATE disbursement_request_line l
        SET advance_payment_id = r.advance_payment_id
        FROM disbursement_request r
        WHERE r.id = l.request_id
          AND r.payment_type = 'advance'
          AND r.advance_payment_id IS NOT NULL
          AND l.display_type IS NULL
        """
    )
