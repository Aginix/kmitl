def migrate(cr, version):
    """The expense report and in-app returns are gone (ADR-0028): an
    agreement waiting on either is simply outstanding again."""
    cr.execute(
        """
        UPDATE advance_payment
           SET state = 'in_progress'
         WHERE state IN ('reported', 'to_reconcile')
        """
    )
