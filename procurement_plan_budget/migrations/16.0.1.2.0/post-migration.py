def migrate(cr, version):
    """ADR-0005: procurement_plan archives every cancelled plan; one that still
    holds money (a net posted allocation at its dimension or an unspent
    reservation) stays visible so that money can be returned (โอนคืนงบลอย)."""
    cr.execute(
        """
        SELECT p.id, p.analytic_account_id
        FROM procurement_plan p
        WHERE p.state = 'cancel' AND p.analytic_account_id IS NOT NULL
          AND (
            EXISTS (
                SELECT 1 FROM budget_move_line l
                WHERE l.procurement_plan_analytic_id = p.analytic_account_id
                  AND l.parent_state = 'posted'
                  AND l.move_type IN ('appropriation', 'entry')
                GROUP BY l.procurement_plan_analytic_id
                HAVING ROUND(SUM(l.balance)::numeric, 2) != 0
            )
            OR EXISTS (
                SELECT 1 FROM budget_commitment c
                WHERE c.procurement_plan_id = p.id
                  AND c.state IN ('reserved', 'partial')
            )
          )
        """
    )
    rows = cr.fetchall()
    if not rows:
        return
    cr.execute(
        "UPDATE procurement_plan SET active = TRUE WHERE id IN %s",
        (tuple(r[0] for r in rows),),
    )
    cr.execute(
        "UPDATE account_analytic_account SET active = TRUE WHERE id IN %s",
        (tuple(r[1] for r in rows),),
    )
