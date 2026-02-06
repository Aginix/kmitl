def migrate(cr, version):
    """Uninstall deprecated modules merged into budget."""
    cr.execute("""
        UPDATE ir_module_module
        SET state = 'to remove'
        WHERE name IN ('budget_account_root', 'budget_analytic_account')
        AND state = 'installed'
    """)
