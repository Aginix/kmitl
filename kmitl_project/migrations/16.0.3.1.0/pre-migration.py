def migrate(cr, version):
    """Expense Control (ADR-0013) is on by default for new projects only: add
    the column before the ORM so existing projects start with it off."""
    if not version:
        return
    cr.execute(
        "ALTER TABLE kmitl_project ADD COLUMN IF NOT EXISTS expense_control boolean"
    )
    cr.execute("UPDATE kmitl_project SET expense_control = false")
