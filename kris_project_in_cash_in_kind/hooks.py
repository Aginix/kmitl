def post_init_hook(cr, registry):
    """Backfill in_cash from project_value on existing research projects.

    When kris_project_in_cash_in_kind is installed onto a database that already
    holds research projects, the freshly-added in_cash and in_kind columns
    default to 0. The stored compute would then set project_value = 0 on those
    rows on the next recompute, wiping the amounts. Seeding in_cash from the
    existing project_value ensures the derivation lands on the same total.
    """
    cr.execute(
        """
        SELECT res_id
        FROM ir_model_data
        WHERE module = 'kris_project'
          AND name = 'project_category_research'
          AND model = 'kris.project.category'
        """
    )
    row = cr.fetchone()
    if not row:
        return
    research_id = row[0]
    cr.execute(
        """
        UPDATE kris_project
        SET in_cash = project_value,
            in_kind = 0
        WHERE project_category_id = %s
          AND COALESCE(in_cash, 0) = 0
          AND COALESCE(in_kind, 0) = 0
          AND COALESCE(project_value, 0) <> 0
        """,
        (research_id,),
    )
