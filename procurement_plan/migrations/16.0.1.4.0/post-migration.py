def migrate(cr, version):
    """ADR-0005: ยกเลิก is now only the state a soft-deleted plan ends in, so
    existing cancelled plans are archived (with their analytic account) to read
    as soft-deleted. The budget layer re-activates any that still hold money,
    so that money can be returned."""
    cr.execute(
        """
        UPDATE procurement_plan SET active = FALSE
        WHERE state = 'cancel' AND active IS NOT FALSE
        RETURNING analytic_account_id
        """
    )
    analytic_ids = tuple(row[0] for row in cr.fetchall() if row[0])
    if analytic_ids:
        cr.execute(
            "UPDATE account_analytic_account SET active = FALSE WHERE id IN %s",
            (analytic_ids,),
        )
